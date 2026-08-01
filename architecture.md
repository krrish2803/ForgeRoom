# System Architecture & Flow

This document details the system design, communication protocols, and data models of **ForgeRoom**.

---

## 🏗️ 1. High-Level Architecture Topology

ForgeRoom uses a decoupled architecture. The frontend is a SPA client, and the backend is a Python FastAPI service. MongoDB Atlas acts as the shared persistence layer.

```mermaid
graph TD
    Client[SPA Client: HTML/JS/Three.js]
    Backend[FastAPI Backend Server]
    DB[(MongoDB Atlas Database)]
    NVIDIA[NVIDIA NIM completions API]
    Tavily[Tavily Search API]

    Client <-->|HTTP REST & WebSockets| Backend
    Backend <-->|Motor Async Driver| DB
    Backend -->|SSE Stream / POST| NVIDIA
    Backend -->|JSON POST| Tavily
```

---

## 🔄 2. End-to-End Core Flow Diagram

Here is a visual map of the operational workflow when a user enters the workspace, uploads a document, triggers a research query, and processes cascaded AI pipelines.

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Collaborator
    participant Client as SPA Frontend (app.js)
    participant Server as FastAPI Server (main.py)
    participant DB as MongoDB Atlas
    participant Tavily as Tavily Web Search API
    participant LLM as NVIDIA NIM Llama 3.1

    %% 1. Room loading
    User->>Client: Open Room Workspace
    Client->>Server: GET /api/rooms/{id} (Check Token)
    Server->>DB: Query Room & User Role
    DB-->>Server: Return Room Meta & Role (Owner/Editor/Viewer)
    Server-->>Client: Returns Workspace details
    Client->>Server: Connect WS (ws://localhost:8002/ws/{room_id})
    Server-->>Client: WebSocket Connected (Joins Presence)

    %% 2. Document upload
    User->>Client: Upload Contract Clause
    Client->>Server: POST /api/rooms/{id}/contract
    Server->>DB: Update Room contract_text
    Server->>DB: Log Audit Trail (contract_uploaded)
    Server-->>Client: 200 OK (Updates Canvas)

    %% 3. Live Research Tool
    User->>Client: Open Research Modal & Submit Topic
    Client->>Server: POST /api/rooms/{id}/research {"query": "..."}
    Server->>Server: Initialize SSE Stream Response
    Server->>Client: Stream Status: searching web...
    Server->>Tavily: POST https://api.tavily.com/search
    Tavily-->>Server: Return Web Snippets & Links
    Server->>Client: Stream Status: synthesizing...
    Server->>LLM: Stream Completions (Query + Web Context)
    LLM-->>Server: Yield report token chunks
    Server->>Client: Stream Chunk to WebSocket Room
    Client-->>User: Renders streaming Markdown report in chat log
    Server->>DB: Save Message & Insert Canvas Card (draft)
    Server->>Client: Stream Status: completed (reload Canvas)

    %% 4. Sequential Chain execution
    User->>Client: Send "@ForgeBot summarize" (Chain Workflow Active)
    Client->>Server: POST /api/agent/respond
    Server->>DB: Fetch Active Pipeline Chain Configuration
    Server->>LLM: Execute Step 1 (Legal Analyst)
    LLM-->>Server: Return Step 1 completions
    Server->>Client: Broadcast stream tokens
    Server->>LLM: Execute Step 2 (Critic + Step 1 context)
    LLM-->>Server: Return Step 2 completions
    Server->>Client: Broadcast stream tokens
    Server->>DB: Save Chain Log & update Canvas
```

---

## 💾 3. Database Data Schema & Relationships

Below is the entity relationship layout representing MongoDB Atlas collections and references:

```mermaid
erDiagram
    users ||--o{ org_members : "belongs to"
    organizations ||--o{ org_members : "has members"
    organizations ||--o{ rooms : "scopes"
    organizations ||--o{ org_agents : "customizes"
    org_agents ||--o{ org_agent_versions : "versions history"
    organizations ||--o{ org_agent_chains : "defines pipelines"
    rooms ||--o{ messages : "contains"
    rooms ||--o{ agent_outputs : "displays canvas cards"
    rooms ||--o{ versions : "snapshots"
    organizations ||--o{ org_audit_logs : "records logs"

    users {
        ObjectId id
        string name
        string email
        string hashed_password
        datetime created_at
    }

    organizations {
        UUID id
        string name
        string created_by
        string subscription_plan
        datetime created_at
    }

    org_members {
        ObjectId id
        UUID org_id
        string user_id
        string role "owner | editor | viewer"
        datetime joined_at
    }

    rooms {
        UUID id
        string name
        UUID org_id
        string created_by
        string contract_text
        string active_agent_id
        UUID active_chain_id
        datetime created_at
    }

    messages {
        ObjectId id
        UUID room_id
        string user_id
        string username
        string content
        string message_type
        datetime created_at
    }

    agent_outputs {
        ObjectId id
        UUID room_id
        ObjectId message_id
        string title
        string content
        string status "draft | finalized"
        datetime created_at
    }

    versions {
        UUID id
        UUID room_id
        int version_number
        string label
        string snapshot_contract
        datetime created_at
    }

    org_agents {
        ObjectId id
        UUID org_id
        string agent_id "slug"
        string system_prompt
        string model_name
        float temperature
        datetime updated_at
    }

    org_agent_versions {
        ObjectId id
        UUID org_id
        string agent_id
        int version
        string system_prompt
        datetime created_at
    }

    org_agent_chains {
        UUID id
        UUID org_id
        string name
        list steps "list of agent slugs"
        datetime created_at
    }

    org_audit_logs {
        ObjectId id
        UUID org_id
        string actor_username
        string action "room_created | member_invited..."
        string details
        datetime timestamp
    }
```

---

## 🔒 4. Role-Based Access Control (RBAC) Permissions Matrix

The backend enforces strict validation gates during REST calls and WebSocket frames based on membership mapping:

| Endpoint Area | Required Roles (Org Scope) | Action Result |
| :--- | :--- | :--- |
| **`POST /rooms`** | Owner, Editor | Success (Creates room scoped to active organization) |
| **`POST /rooms/{id}/contract`** | Owner, Editor | Success (Updates document context) |
| **`POST /rooms/{id}/snapshots`** | Owner, Editor | Success (Freezes current version) |
| **`POST /rooms/{id}/branch`** | Owner, Editor | Success (Spins up clone workspace) |
| **`POST /rooms/{id}/research`** | Owner, Editor | Success (Launches Tavily live crawler) |
| **`PATCH /orgs/{id}/agents/{agent_id}`** | Owner | Success (Edits AI instructions / prompts) |
| **`POST /orgs/{id}/agents/{agent_id}/revert`**| Owner | Success (Rolls back AI prompt version) |
| **`POST /orgs/{id}/chains`** | Owner | Success (Builds sequential multi-agent cascades) |
| **Viewer Operations (All)** | Viewer | **Blocked (`403 Forbidden` / Websocket Error Alert)** |
