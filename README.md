# ForgeRoom

> **Work Together With Your AI. Not Beside It.**
> A Real-Time Multiplayer Collaborative Workspace with Custom AI Agent Orchestration, Versioning, and Live Deep Research.

---

## 📖 Table of Contents
1. [Problem Statement](#-problem-statement)
2. [Proposed Solution](#-proposed-solution)
3. [Impact & Value Creation](#-impact--value-creation)
4. [Key Features](#-key-features)
5. [System Architecture Overview](#-system-architecture-overview)
6. [File Structure](#-file-structure)
7. [Installation & Setup](#-installation--setup)
8. [Testing Suite](#-testing-suite)
9. [Deployment](#-deployment)
10. [License](#-license)

---

## ❓ Problem Statement

In the modern enterprise, collaboration with AI is broken:
- **Solo Silos**: Individuals interact with ChatGPT, Claude, or local assistants in isolated browser tabs. Team context and decision-making history are lost.
- **Asymmetric Interactivity**: Teams cannot redirect outputs, intervene mid-stream, or review compliance steps once an LLM starts generating content.
- **Audit & Compliance Gaps**: Law firms, sales groups, and tech organizations cannot safely leverage AI without strict Role-Based Access Control (RBAC) and compliance trails detailing who accessed or generated sensitive documents.

---

## 💡 Proposed Solution

**ForgeRoom** solves this by introducing a multiplayer cooperative command center where teams and AI agents collaborate in real-time.
- **Shared Collaborative Canvas**: Think Google Docs, but where multiple human users and cascaded AI pipelines stream edits in real-time.
- **Custom Agent Library**: Organizations can override prompts, maintain version rollback history, and build sequential multi-agent chains.
- **Live Internet Deep Research**: Connects to the live web via Tavily to extract fresh insights and stream detailed summaries directly into the room.

---

## 📈 Impact & Value Creation

- **Zero Asymmetric Overhead**: Co-author documents in real-time alongside team members and AI. Eliminate the need to copy-paste outputs back and forth.
- **Enterprise Grade Confidence**: Owners have complete control. Strict RBAC hides input forms and action buttons from Viewers, while audit trail ledgers record every modification.
- **Tailored AI Workflows**: Custom prompt overrides allow organizations to build specialized assistants (e.g., Legal Analyst ➔ Critic ➔ Summarizer) tailored to their proprietary guidelines.

---

## 🌟 Key Features

1. **Multiplayer Live Workspace**: WebSocket-based multiplayer rooms with presence tracking and active cursors.
2. **Organization Containers & RBAC**: Segment rooms by company. Enforces Owner, Editor, and Viewer permission levels.
3. **Seeded Agent Library**: Pre-built personas (Legal, Sales, Code Review, etc.) with custom prompt overrides and rollback reversion history.
4. **Agent Pipeline Chaining**: Sequential workflows where Step $N$ automatically consumes output and instructions from Step $N-1$.
5. **Tavily Live Web Search**: A Deep Research Tool that pulls current web data, extracts snippets, and synthesizes structured reports.
6. **Snapshots & Branching**: Freeze document states at a specific label and spin up a new room branched from that snapshot.
7. **Document Exports**: Download collaborative outputs to PDF, Markdown, or copy as raw JSON.

---

## 🏗️ System Architecture Overview

ForgeRoom is built using a modern, decoupled architecture:
- **Frontend SPA**: Lightweight Single Page Application built on HTML5, custom CSS styling, and Three.js 3D animations. Serves as a responsive, real-time client.
- **FastAPI Backend**: Python-based API server handling WebSocket orchestration, Server-Sent Events (SSE) streaming, JWT session security, and REST endpoints.
- **MongoDB Atlas**: Cloud-hosted document store keeping user details, rooms, canvas outputs, messages, audit logs, and custom agent versions.
- **External APIs**: Integrates with NVIDIA NIM endpoints for LLM generations and Tavily APIs for real-time web crawlers.

For a detailed flow diagram and service overview, please check [architecture.md](architecture.md).

---

## 📂 File Structure

```text
ForgeRoom/
├── Dockerfile                  # Production Docker deployment configuration
├── docker-compose.yml          # Local container orchestration
├── LICENSE                     # MIT License details
├── README.md                   # Project documentation
├── architecture.md             # Visual project flow and data mapping
├── index.html                  # Single Page Application HTML & layout
├── app.js                      # Three.js animation setup & dynamic JS controllers
├── style.css                   # Custom global CSS styling
├── landing.html                # Standalone marketing landing page
├── backend/
│   ├── app/
│   │   ├── auth/               # User registration, login, and security routes
│   │   ├── rooms/              # Room creation, snapshotting, and branching routes
│   │   ├── agent/              # NVIDIA LLM streaming and Tavily research endpoints
│   │   ├── agent_custom/       # Agent library edits, version rollbacks, and chaining
│   │   ├── database.py         # MongoDB connections and indexes seeding setup
│   │   ├── config.py           # App Settings loader (Pydantic environment variables)
│   │   └── main.py             # FastAPI entry point, lifespan, CORS, and WebSocket router
│   ├── requirements.txt        # Backend python dependencies list
│   ├── test_mvp_features.py    # Integration test for core features
│   ├── test_org_rbac.py        # Integration test for Organization RBAC roles
│   ├── test_agent_library.py   # Integration test for custom agents and workflows
│   └── test_research_tool.py   # Integration test for Tavily web lookup streams
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+ installed.
- MongoDB Atlas account (or local MongoDB running).
- NVIDIA API Key & Tavily API Key.

### 1. Configure Environment Variables
Navigate to the `backend/` folder and create a `.env` file from `.env.example`:
```bash
cd backend
cp .env.example .env
```
Fill in the credentials:
```env
MONGODB_URL=your_mongodb_atlas_connection_string
DATABASE_NAME=forgeroom
JWT_SECRET_KEY=generate_a_random_jwt_secret
NVIDIA_API_KEY=your_nvidia_nim_api_key
TAVILY_API_KEY=your_tavily_search_api_key
```

### 2. Install Dependencies & Run Backend
Install python packages and start the dev server:
```bash
pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 3. Open the Frontend
Since the FastAPI backend serves static files, you can access the frontend directly by visiting:
**`http://localhost:8002/landing.html`** or **`http://localhost:8002/index.html`** in your browser.

---

## 🧪 Testing Suite

We provide a comprehensive suite of integration tests to verify the backend end-to-end. Run them from the `backend/` directory:

```bash
# Verify packages imports and syntax
python3 verify_backend.py

# Test core MVP features (Auth, LLM response, snapshat, branching, etc.)
python3 test_mvp_features.py

# Test Org creation and Owner/Editor/Viewer RBAC restrictions
python3 test_org_rbac.py

# Test Agent Library overrides, rollback history, and pipeline chains
python3 test_agent_library.py

# Test live web queries and markdown synthesis via Tavily Search API
python3 test_research_tool.py
```

---

## 🚀 Deployment

ForgeRoom is production-ready and fully containerized.

### Build and Run with Docker
```bash
# Build the unified image
docker build -t forgeroom .

# Run the container (exposing API and Frontend at port 8002)
docker run -p 8002:8002 --env-file backend/.env forgeroom
```

### Or using Docker Compose
```bash
docker-compose up --build
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
