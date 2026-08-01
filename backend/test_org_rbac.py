import requests
import sys
import json
import time
import os

API_URL = os.getenv("API_URL", "http://localhost:8002")

print("====================================================")
print("  FORGEROOM ORG WORKSPACES & RBAC INTEGRATION TEST ")
print("====================================================")

# Generate unique names & emails
rand = int(time.time())
owner_email = f"owner_{rand}@testforgeroom.com"
editor_email = f"editor_{rand}@testforgeroom.com"
viewer_email = f"viewer_{rand}@testforgeroom.com"
test_password = "secure_password_123"

# 1. REGISTER USERS
print("\n[1/9] Registering Test Users (Owner, Editor, Viewer)...")
try:
    # Register Owner
    res = requests.post(f"{API_URL}/api/auth/register", json={
        "name": "Org Owner", "email": owner_email, "password": test_password
    })
    assert res.status_code == 201, "Owner registration failed"
    owner_id = res.json()["_id"]
    
    # Register Editor
    res = requests.post(f"{API_URL}/api/auth/register", json={
        "name": "Org Editor", "email": editor_email, "password": test_password
    })
    assert res.status_code == 201, "Editor registration failed"
    editor_id = res.json()["_id"]
    
    # Register Viewer
    res = requests.post(f"{API_URL}/api/auth/register", json={
        "name": "Org Viewer", "email": viewer_email, "password": test_password
    })
    assert res.status_code == 201, "Viewer registration failed"
    viewer_id = res.json()["_id"]
    
    print("✓ Successfully registered all 3 test users.")
except Exception as e:
    print(f"❌ User Registration Error: {e}")
    sys.exit(1)

# 2. LOGIN USERS & GET TOKENS
print("\n[2/9] Logging in Users & Acquiring tokens...")
try:
    # Login Owner
    res = requests.post(f"{API_URL}/api/auth/login", json={"email": owner_email, "password": test_password})
    assert res.status_code == 200, "Owner login failed"
    owner_token = res.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Login Editor
    res = requests.post(f"{API_URL}/api/auth/login", json={"email": editor_email, "password": test_password})
    assert res.status_code == 200, "Editor login failed"
    editor_token = res.json()["access_token"]
    editor_headers = {"Authorization": f"Bearer {editor_token}"}
    
    # Login Viewer
    res = requests.post(f"{API_URL}/api/auth/login", json={"email": viewer_email, "password": test_password})
    assert res.status_code == 200, "Viewer login failed"
    viewer_token = res.json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    
    print("✓ Tokens acquired successfully.")
except Exception as e:
    print(f"❌ Login Error: {e}")
    sys.exit(1)

# 3. CREATE ORGANIZATION & JOIN MEMBERS
print("\n[3/9] Creating Organization & Inviting Members...")
try:
    # Owner creates Org
    res = requests.post(f"{API_URL}/api/orgs", json={"name": "Acme Law Corp"}, headers=owner_headers)
    assert res.status_code == 201, "Org creation failed"
    org_data = res.json()
    org_id = org_data["_id"]
    print(f"✓ Created Org: '{org_data['name']}' with ID: {org_id}")
    
    # Owner invites Editor
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/members", json={"email": editor_email, "role": "editor"}, headers=owner_headers)
    assert res.status_code == 200, "Invite editor failed"
    
    # Owner invites Viewer
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/members", json={"email": viewer_email, "role": "viewer"}, headers=owner_headers)
    assert res.status_code == 200, "Invite viewer failed"
    
    # Get members list & verify
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/members", headers=owner_headers)
    members = res.json()
    assert len(members) == 3, "Wrong member count"
    print("✓ Successfully invited Editor and Viewer to Organization.")
except Exception as e:
    print(f"❌ Org Setup Error: {e}")
    sys.exit(1)

# 4. CREATE ROOM UNDER ORG
print("\n[4/9] Creating Room under Organization Scope...")
try:
    # Editor creates Room
    res = requests.post(f"{API_URL}/api/rooms", json={
        "name": "Acme NDA Review Case",
        "created_by_id": editor_id,
        "org_id": org_id
    }, headers=editor_headers)
    assert res.status_code == 201, "Room creation in Org failed"
    room_data = res.json()
    room_id = room_data["_id"]
    print(f"✓ Room created in Org context. ID: {room_id}")
    
    # Verify User Roles loaded inside room details
    res_editor = requests.get(f"{API_URL}/api/rooms/{room_id}", headers=editor_headers)
    assert res_editor.json()["user_role"] == "editor", "Incorrect role mapping for Editor"
    
    res_viewer = requests.get(f"{API_URL}/api/rooms/{room_id}", headers=viewer_headers)
    assert res_viewer.json()["user_role"] == "viewer", "Incorrect role mapping for Viewer"
    print("✓ Verified room user_role retrieval mappings.")
except Exception as e:
    print(f"❌ Room Setup Error: {e}")
    sys.exit(1)

# 5. TEST RBAC WRITE ACCESS (EDITOR YES, VIEWER NO)
print("\n[5/9] Testing Role-Based Write Access Permissions (RBAC)...")
try:
    # A. Upload Contract Clause
    # Editor can do it
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/upload-contract", json={"contract_text": "Confidentiality Term"}, headers=editor_headers)
    assert res.status_code == 200, "Editor contract upload failed"
    # Viewer is blocked
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/upload-contract", json={"contract_text": "Viewer Hacked"}, headers=viewer_headers)
    assert res.status_code == 403, "Viewer was not blocked from uploading contract"
    print("✓ Checked: Editor can upload contract clauses; Viewer is blocked (403 Forbidden).")
    
    # B. Create Snapshot Version
    # Editor can do it
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/versions", json={"label": "Pre-negotiation Snapshot"}, headers=editor_headers)
    assert res.status_code == 200, "Editor version creation failed"
    version_id = res.json()["version_id"]
    # Viewer is blocked
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/versions", json={"label": "Viewer Hacked Snapshot"}, headers=viewer_headers)
    assert res.status_code == 403, "Viewer was not blocked from saving snapshots"
    print("✓ Checked: Editor can create transcript snapshots; Viewer is blocked.")
    
    # C. Branch workspace from Version
    # Editor can do it
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/versions/{version_id}/branch", json={"name": "Acme NDA Branch A"}, headers=editor_headers)
    assert res.status_code == 200, "Editor branching failed"
    # Viewer is blocked
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/versions/{version_id}/branch", json={"name": "Viewer Branch"}, headers=viewer_headers)
    assert res.status_code == 403, "Viewer was not blocked from branching"
    print("✓ Checked: Editor can branch rooms; Viewer is blocked.")
except Exception as e:
    print(f"❌ RBAC Permissions Error: {e}")
    sys.exit(1)

# 6. TEST COMPLIANCE AUDIT TRAIL LOGGING
print("\n[6/9] Testing Compliance Audit Trail Logging...")
try:
    # Owner fetches logs (Allowed)
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/audit-logs", headers=owner_headers)
    assert res.status_code == 200, "Owner audit log fetch failed"
    logs = res.json()
    actions = [l["action"] for l in logs]
    print(f"✓ Audited actions found: {actions}")
    assert "room_created" in actions, "Room creation was not logged"
    assert "contract_uploaded" in actions, "Contract clause upload was not logged"
    assert "version_created" in actions, "Version snapshot was not logged"
    
    # Viewer fetches logs (Blocked)
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/audit-logs", headers=viewer_headers)
    assert res.status_code == 403, "Viewer was not blocked from viewing audit logs"
    print("✓ Checked: Compliance logs recorded all key write events; Viewer is blocked.")
except Exception as e:
    print(f"❌ Audit Trail Logging Error: {e}")
    sys.exit(1)

# 7. TEST SHARED AI CONFIGS (FORGEBOT SETTINGS)
print("\n[7/9] Testing Shared Agent Configurations (ForgeBot)...")
try:
    # Fetch default config
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/agent-config", headers=editor_headers)
    assert res.status_code == 200, "Fetch agent config failed"
    cfg = res.json()
    print(f"✓ Default Org Prompt instruction: '{cfg['system_prompt']}'")
    
    # Owner updates config
    new_prompt = "You are a senior partner at Acme Law Corp reviewing high-risk contracts."
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/agent-config", json={
        "system_prompt": new_prompt,
        "temperature": 0.2,
        "model_name": "meta/llama-3.1-8b-instruct"
    }, headers=owner_headers)
    assert res.status_code == 200, "Owner agent config save failed"
    
    # Viewer tries to save config
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/agent-config", json={
        "system_prompt": "Viewer hack", "temperature": 0.9
    }, headers=viewer_headers)
    assert res.status_code == 403, "Viewer was not blocked from editing config"
    print("✓ Checked: Owner can update shared AI configuration; Viewer is blocked.")
except Exception as e:
    print(f"❌ Shared Agent Configs Error: {e}")
    sys.exit(1)

# 8. TEST ORG BILLING & PLAN MANAGEMENT
print("\n[8/9] Testing Organization Billing Plans...")
try:
    # Owner fetches billing info
    res = requests.get(f"{API_URL}/api/orgs/{org_id}/billing", headers=owner_headers)
    assert res.status_code == 200, "Owner billing fetch failed"
    billing = res.json()
    assert billing["billing_plan"] == "Free", "Default plan was not Free"
    
    # Owner updates plan to Enterprise
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/billing", json={"billing_plan": "Enterprise"}, headers=owner_headers)
    assert res.status_code == 200, "Owner billing plan save failed"
    
    # Viewer tries to update billing plan
    res = requests.post(f"{API_URL}/api/orgs/{org_id}/billing", json={"billing_plan": "Premium"}, headers=viewer_headers)
    assert res.status_code == 403, "Viewer was not blocked from changing billing plans"
    print("✓ Checked: Owner can manage subscription plans; Viewer is blocked.")
except Exception as e:
    print(f"❌ Billing Plans Error: {e}")
    sys.exit(1)

# 9. CONCLUDE SUCCESS
print("\n[9/9] Verification Checks Completed!")
print("\n✓ ALL INTEGRATION TESTS PASSED SUCCESSFULLY! Org Workspaces & RBAC controls are fully operational.")
print("====================================================")
