import requests
import sys
import json
import time
import os

API_URL = os.getenv("API_URL", "http://localhost:8002")

print("====================================================")
print("     FORGEROOM AI AGENT LIBRARY & CHAINING TEST     ")
print("====================================================")

# Generate unique names & emails
rand = int(time.time())
owner_email = f"agent_owner_{rand}@testforgeroom.com"
test_password = "secure_password_123"

# 1. REGISTER OWNER
print("\n[1/10] Registering Org Owner...")
try:
    res = requests.post(f"{API_URL}/api/auth/register", json={
        "name": "Library Admin", "email": owner_email, "password": test_password
    })
    assert res.status_code == 201, f"Owner registration failed: {res.text}"
    owner_id = res.json()["_id"]
    print("✓ Successfully registered owner.")
except Exception as e:
    print(f"❌ Owner Registration Error: {e}")
    sys.exit(1)

# 2. LOGIN OWNER & GET TOKEN
print("\n[2/10] Logging in Org Owner...")
try:
    res = requests.post(f"{API_URL}/api/auth/login", json={"email": owner_email, "password": test_password})
    assert res.status_code == 200, "Owner login failed"
    owner_token = res.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}
    print("✓ Tokens acquired successfully.")
except Exception as e:
    print(f"❌ Login Error: {e}")
    sys.exit(1)

# 3. CREATE ORGANIZATION
print("\n[3/10] Creating Organization...")
try:
    res = requests.post(f"{API_URL}/api/orgs", json={"name": "Aegis Legal Solutions"}, headers=owner_headers)
    assert res.status_code == 201, "Org creation failed"
    org_data = res.json()
    org_id = org_data["_id"]
    print(f"✓ Created Org: '{org_data['name']}' with ID: {org_id}")
except Exception as e:
    print(f"❌ Org Setup Error: {e}")
    sys.exit(1)

# 4. LIST SEEDED LIBRARY AGENTS
print("\n[4/10] Fetching Seeded AI Library Agents...")
try:
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/agents", headers=owner_headers)
    assert res.status_code == 200, "Failed to list agents"
    agents = res.json()
    print(f"✓ Retrieved {len(agents)} agents from library:")
    for a in agents:
        print(f"   - [{a['slug']}] {a['icon']} {a['name']} (Custom: {a.get('is_custom')}, Overridden: {a.get('is_overridden')})")
    
    # Assert default seeded agents exist
    slugs = [a['slug'] for a in agents]
    assert "legal-analyst" in slugs, "Seed agent 'legal-analyst' missing"
    assert "critic" in slugs, "Seed agent 'critic' missing"
except Exception as e:
    print(f"❌ Library Fetch Error: {e}")
    sys.exit(1)

# 5. OVERRIDE AGENT PROMPT & VERIFY
print("\n[5/10] Editing Seeded Agent (legal-analyst)...")
try:
    # Get original legal-analyst settings
    analyst = next(a for a in agents if a['slug'] == 'legal-analyst')
    original_prompt = analyst['system_prompt']
    
    # Update prompt
    new_prompt = original_prompt + "\nADDITIONAL RULE: Highlight liability clauses in UPPERCASE."
    payload = {
        "name": analyst["name"],
        "description": analyst["description"],
        "icon": analyst["icon"],
        "system_prompt": new_prompt,
        "model_name": analyst.get("suggested_model") or analyst.get("model_name"),
        "temperature": analyst.get("temperature", 0.5)
      }
    res = requests.patch(f"{API_URL}/api/orgs/{org_id}/agents/legal-analyst", json=payload, headers=owner_headers)
    assert res.status_code == 200, f"Failed to override agent: {res.text}"
    print("✓ Successfully overridden system prompt.")
    
    # Re-fetch agents list and verify Overridden badge status
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/agents", headers=owner_headers)
    updated_agents = res.json()
    updated_analyst = next(a for a in updated_agents if a['slug'] == 'legal-analyst')
    assert updated_analyst['is_overridden'] is True, "is_overridden status failed to update"
    print("✓ Verified 'is_overridden' status successfully.")
except Exception as e:
    print(f"❌ Edit Agent Error: {e}")
    sys.exit(1)

# 6. GET VERSIONS HISTORY & ROLLBACK
print("\n[6/10] Testing Versions History & Rollback Revert...")
try:
    # Get version history
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/agents/legal-analyst/versions", headers=owner_headers)
    assert res.status_code == 200, "Failed to get version history"
    versions = res.json()
    print(f"✓ Found {len(versions)} recorded versions:")
    for v in versions:
        print(f"   - Version {v['version']} (Saved at {v['updated_at']})")
        
    assert len(versions) >= 2, "Should have at least 2 versions (seed + edited)"
    
    # Revert to version 1 (original seed prompt)
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/agents/legal-analyst/revert", json={"version": 1}, headers=owner_headers)
    assert res.status_code == 200, "Revert call failed"
    print("✓ Triggered revert back to Version 1.")
    
    # Verify rollback output system prompt
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/agents", headers=owner_headers)
    latest_agents = res.json()
    reverted_analyst = next(a for a in latest_agents if a['slug'] == 'legal-analyst')
    assert "ADDITIONAL RULE" not in reverted_analyst['system_prompt'], "Rollback system prompt did not restore original settings"
    print("✓ Verified rollback prompt successfully restored original instructions.")
except Exception as e:
    print(f"❌ Version/Rollback Error: {e}")
    sys.exit(1)

# 7. CREATE NEW CUSTOM AI AGENT
print("\n[7/10] Creating Custom AI Agent (risk-compliance-expert)...")
try:
    payload = {
        "name": "Risk & Compliance Expert",
        "description": "Scans documents for regulatory compliance failures",
        "icon": "⚖️",
        "system_prompt": "You are a regulatory risk expert. Highlight policy violations.",
        "model_name": "meta/llama-3.1-70b-instruct",
        "temperature": 0.3
    }
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/agents", json=payload, headers=owner_headers)
    assert res.status_code in [200, 201], f"Failed to create custom agent: {res.text}"
    custom_agent = res.json()
    custom_slug = custom_agent.get("slug") or custom_agent.get("agent_id")
    print(f"✓ Created Custom Agent: '{custom_agent['name']}' with slug: {custom_slug}")
    
    # Verify custom status
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/agents", headers=owner_headers)
    agent_list = res.json()
    expert = next(a for a in agent_list if a['slug'] == custom_slug)
    assert expert['is_custom'] is True, "Custom status flag not set correctly"
    print("✓ Verified custom agent flags.")
except Exception as e:
    print(f"❌ Custom Agent Creation Error: {e}")
    sys.exit(1)

# 8. CREATE MULTI-AGENT PIPELINE CHAIN WORKFLOW
print("\n[8/10] Building Multi-Agent Pipeline Chain (NDAAuditPipeline)...")
try:
    payload = {
        "name": "NDA Audit Pipeline",
        "description": "Analyst -> critic workflow",
        "agents": ["legal-analyst", custom_slug]
    }
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/chains", json=payload, headers=owner_headers)
    assert res.status_code in [200, 201], f"Failed to create pipeline chain: {res.text}"
    chain_data = res.json()
    chain_id = chain_data["id"]
    print(f"✓ Created Pipeline Chain with ID: {chain_id}")
    
    # Verify chain listing
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/chains", headers=owner_headers)
    chains = res.json()
    assert len(chains) >= 1, "Chains fetch returned empty list"
    print("✓ Confirmed pipeline listing returns newly created chain.")
except Exception as e:
    print(f"❌ Chaining Setup Error: {e}")
    sys.exit(1)

# 9. SET ROOM ACTIVE WORKFLOW CHAIN
print("\n[9/10] Assigning Pipeline Workflow to Active Room...")
try:
    # Create org room
    res = requests.post(f"{API_URL}/api/rooms", json={"name": "Audit Room", "org_id": org_id, "created_by_id": owner_id}, headers=owner_headers)
    assert res.status_code == 201, f"Room creation failed: {res.text}"
    room_id = res.json()["_id"]
    print(f"✓ Created Org Room with ID: {room_id}")
    
    # Save active workflow chain
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/workflow", json={
        "active_agent_id": None,
        "active_chain_id": chain_id
    }, headers=owner_headers)
    assert res.status_code == 200, "Assign workflow failed"
    print("✓ Successfully assigned active pipeline chain to room.")
    
    # Fetch room details and assert DB values
    res = requests.get(f"{API_URL}/api/rooms/{room_id}", headers=owner_headers)
    room_details = res.json()["room"]
    assert room_details["active_chain_id"] == chain_id, "active_chain_id mismatch in DB record"
    assert room_details["active_agent_id"] is None, "active_agent_id should be cleared"
    print("✓ Verified active workflow configuration is persistent in database.")
except Exception as e:
    print(f"❌ Room Settings Error: {e}")
    sys.exit(1)

# 10. MULTI-AGENT EXECUTION STREAMING
print("\n[10/10] Triggering Chained Agent Execution (Streams Step 1 -> Step 2)...")
try:
    # Trigger generation respondent
    payload = {
        "room_id": room_id,
        "user_message": "Please review if this contract has standard clauses"
    }
    
    # Make request to stream SSE output
    res = requests.post(f"{API_URL}/api/agent/respond", json=payload, headers=owner_headers, stream=True)
    assert res.status_code == 200, f"Streaming trigger failed: {res.text}"
    
    print("✓ Streaming SSE connection established. Printing stream events:")
    for line in res.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                data = json.loads(decoded_line[6:])
                if data["type"] == "token":
                    # Print token content inline
                    sys.stdout.write(data["content"])
                    sys.stdout.flush()
                elif data["type"] == "done":
                    print("\n✓ Stream completed.")
                    break
    
    print("\n✓ Verification of all parts of Feature 13 completed successfully!")
except Exception as e:
    print(f"❌ Chained Streaming Error: {e}")
    sys.exit(1)

print("\n====================================================")
print("   🎉 ALL AI AGENT LIBRARY & CHAIN TESTS PASSED!   ")
print("====================================================")
