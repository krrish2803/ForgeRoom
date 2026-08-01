import requests
import sys
import json
import time

API_URL = "http://localhost:8002"

print("====================================================")
print("   FORGEROOM MVP SYSTEM FEATURE INTEGRATION TEST   ")
print("====================================================")

# Generate unique credentials
rand = int(time.time())
test_name = f"Test Lawyer {rand}"
test_email = f"lawyer_{rand}@testforgeroom.com"
test_password = "secure_password_123"

# 1. TEST AUTHENTICATION - REGISTER
print("\n[1/10] Testing User Registration...")
try:
    reg_res = requests.post(f"{API_URL}/api/auth/register", json={
        "name": test_name,
        "email": test_email,
        "password": test_password
    })
    print(f"Status: {reg_res.status_code}")
    assert reg_res.status_code == 201, "Registration failed"
    reg_data = reg_res.json()
    print(f"✓ Registered: {reg_data['name']} ({reg_data['email']})")

    # Register secondary user for invitation checks
    invitee_email = f"invitee_{rand}@testforgeroom.com"
    reg_res2 = requests.post(f"{API_URL}/api/auth/register", json={
        "name": "Invited Collaborator",
        "email": invitee_email,
        "password": test_password
    })
    assert reg_res2.status_code == 201, "Invitee registration failed"
    print(f"✓ Registered Invitee: Invited Collaborator ({invitee_email})")
except Exception as e:
    print(f"❌ Registration Error: {e}")
    sys.exit(1)

# 2. TEST AUTHENTICATION - LOGIN
print("\n[2/10] Testing User Login...")
try:
    login_res = requests.post(f"{API_URL}/api/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    print(f"Status: {login_res.status_code}")
    assert login_res.status_code == 200, "Login failed"
    token_data = login_res.json()
    access_token = token_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    print("✓ Login successful, JWT token acquired.")
except Exception as e:
    print(f"❌ Login Error: {e}")
    sys.exit(1)

# 3. TEST AUTHENTICATION - PROFILE FETCH (/ME)
print("\n[3/10] Testing Fetch User Profile (/me)...")
try:
    me_res = requests.get(f"{API_URL}/api/auth/me", headers=auth_headers)
    print(f"Status: {me_res.status_code}")
    assert me_res.status_code == 200, "Fetch profile failed"
    profile = me_res.json()
    user_id = profile.get("id") or profile.get("_id")
    print(f"✓ Verified Profile: name='{profile['name']}', id='{user_id}'")
except Exception as e:
    print(f"❌ Profile Fetch Error: {e}")
    sys.exit(1)

# 4. TEST ROOMS - CREATE ROOM
print("\n[4/10] Testing Room Creation...")
try:
    create_res = requests.post(f"{API_URL}/api/rooms", json={
        "name": "Integration Test Room",
        "created_by_id": user_id
    }, headers=auth_headers)
    print(f"Status: {create_res.status_code}")
    assert create_res.status_code == 201, "Room creation failed"
    room_data = create_res.json()
    room_id = room_data.get("id") or room_data.get("_id")
    print(f"✓ Created Room: '{room_data.get('name')}' with ID: {room_id}")
except Exception as e:
    print(f"❌ Room Creation Error: {e}")
    sys.exit(1)

# 5. TEST ROOMS - JOIN ROOM
print("\n[5/10] Testing Join Room...")
try:
    join_res = requests.post(f"{API_URL}/api/rooms/{room_id}/join", json={
        "user_id": user_id,
        "username": test_name
    }, headers=auth_headers)
    print(f"Status: {join_res.status_code}")
    assert join_res.status_code == 200, "Join room failed"
    print("✓ Successfully joined room presence.")

    # Test Inviting Collaborator by Email
    print("Inviting secondary teammate by email...")
    invitee_email = f"invitee_{rand}@testforgeroom.com"
    invite_res = requests.post(f"{API_URL}/api/rooms/{room_id}/add-member", json={
        "user_email": invitee_email
    }, headers=auth_headers)
    print(f"Invite Status: {invite_res.status_code}")
    assert invite_res.status_code == 200, "Invite member failed"
    print(f"✓ Invited: {invite_res.json()['username']}")
except Exception as e:
    print(f"❌ Join Room Error: {e}")
    sys.exit(1)

# 6. TEST ROOMS - UPLOAD CONTRACT CLAUSE
print("\n[6/10] Testing Contract Clause Upload...")
clause_text = "LIMITATION OF LIABILITY: Under no circumstances shall either party be liable for any indirect, special, punitive, or consequential damages exceeding $50,000."
try:
    upload_res = requests.post(f"{API_URL}/api/rooms/{room_id}/upload-contract", json={
        "contract_text": clause_text
    }, headers=auth_headers)
    print(f"Status: {upload_res.status_code}")
    assert upload_res.status_code == 200, "Upload contract failed"
    print("✓ Contract clause uploaded successfully.")
except Exception as e:
    print(f"❌ Upload Contract Error: {e}")
    sys.exit(1)

# 7. TEST AGENT - NVIDIA LLM RESPOND STREAM
print("\n[7/10] Testing LangGraph Agent NVIDIA Stream respond...")
try:
    # Trigger AI response. Since it returns a StreamingResponse, we read it chunk-by-chunk.
    print("Sending message: 'Please summarize risks in this Limitation of Liability clause' to @ForgeBot...")
    respond_res = requests.post(f"{API_URL}/api/agent/respond", json={
        "room_id": room_id,
        "user_message": "Please summarize risks in this clause @ForgeBot",
        "conversation_history": []
    }, headers=auth_headers, stream=True)
    
    print(f"Response status: {respond_res.status_code}")
    assert respond_res.status_code == 200, "Agent respond failed"
    
    print("Streaming tokens from NVIDIA API:")
    tokens_count = 0
    for line in respond_res.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data: "):
                payload = json.loads(decoded[6:])
                if payload["type"] == "token":
                    print(payload["content"], end="", flush=True)
                    tokens_count += 1
                elif payload["type"] == "done":
                    print("\n")
                    
    print(f"✓ Agent responded. Received {tokens_count} stream tokens.")
except Exception as e:
    print(f"❌ Agent Response Error: {e}")
    sys.exit(1)

# 8. TEST SNAPSHOTS - SAVE & LIST VERSION
print("\n[8/10] Testing Save & List Snapshot Versions...")
try:
    # Save Snapshot
    snap_res = requests.post(f"{API_URL}/api/rooms/{room_id}/versions", json={
        "user_id": user_id,
        "label": "Post Agent Analysis Review"
    }, headers=auth_headers)
    print(f"Save Status: {snap_res.status_code}")
    assert snap_res.status_code == 200, "Save snapshot failed"
    snap_data = snap_res.json()
    version_id = snap_data["version_id"]
    print(f"✓ Saved Snapshot: Version {snap_data['version_number']} with label: 'Post Agent Analysis Review'")
    
    # List Snapshots
    list_res = requests.get(f"{API_URL}/api/rooms/{room_id}/versions", headers=auth_headers)
    print(f"List Status: {list_res.status_code}")
    assert list_res.status_code == 200, "List snapshots failed"
    versions_list = list_res.json()["versions"]
    print(f"✓ Snapshot list length: {len(versions_list)}")
    assert len(versions_list) > 0, "Snapshot list empty"
except Exception as e:
    print(f"❌ Snapshot Error: {e}")
    sys.exit(1)

# 9. TEST BRANCHING - BRANCH FROM VERSION
print("\n[9/10] Testing Branching Room from snapshot version...")
try:
    branch_res = requests.post(f"{API_URL}/api/rooms/{room_id}/versions/{version_id}/branch", json={
        "user_id": user_id,
        "name": "Branched Alternate Risk Exploration"
    }, headers=auth_headers)
    print(f"Status: {branch_res.status_code}")
    assert branch_res.status_code == 200, "Branch from version failed"
    branch_data = branch_res.json()
    branched_room_id = branch_data["new_room_id"]
    print(f"✓ Branched Room successfully! New Room ID: {branched_room_id}")
except Exception as e:
    print(f"❌ Branching Error: {e}")
    sys.exit(1)

# 10. TEST EXPORTS - MARKDOWN, PDF, COPY TEXT
print("\n[10/10] Testing Native Document Exports...")
try:
    # Export Markdown
    md_res = requests.get(f"{API_URL}/api/rooms/{room_id}/export/markdown", headers=auth_headers)
    print(f"Markdown Export Status: {md_res.status_code}")
    assert md_res.status_code == 200, "Markdown export failed"
    print(f"✓ Markdown content length: {len(md_res.text)} chars")
    
    # Export PDF
    pdf_res = requests.get(f"{API_URL}/api/rooms/{room_id}/export/pdf", headers=auth_headers)
    print(f"PDF Export Status: {pdf_res.status_code}")
    assert pdf_res.status_code == 200, "PDF export failed"
    print(f"✓ PDF binary content length: {len(pdf_res.content)} bytes")
    
    # Export Copy text
    copy_res = requests.get(f"{API_URL}/api/rooms/{room_id}/export/copy", headers=auth_headers)
    print(f"Copy Export Status: {copy_res.status_code}")
    assert copy_res.status_code == 200, "Copy export failed"
    print("✓ Copy JSON check completed.")
except Exception as e:
    print(f"❌ Export Error: {e}")
    sys.exit(1)

# ==========================================
# ADVANCED FEATURES 6-11 TESTS
# ==========================================
print("\n[11/14] Testing Magic Templates...")
try:
    # List Templates
    t_res = requests.get(f"{API_URL}/api/templates", headers=auth_headers)
    print(f"List Templates Status: {t_res.status_code}")
    assert t_res.status_code == 200, "List templates failed"
    templates = t_res.json()["templates"]
    print(f"✓ Templates Seeded: {', '.join([t['name'] for t in templates])}")
    
    # Create Room from Template
    t_create_res = requests.post(f"{API_URL}/api/templates/contract-review/create-room", json={
        "created_by_id": user_id,
        "custom_name": "Test Template Clause Channel"
    }, headers=auth_headers)
    print(f"Template Create Status: {t_create_res.status_code}")
    assert t_create_res.status_code == 200, "Create room from template failed"
    t_room_id = t_create_res.json()["room_id"]
    print(f"✓ Room created from template. ID: {t_room_id}")
except Exception as e:
    print(f"❌ Magic Templates Error: {e}")
    sys.exit(1)

print("\n[12/14] Testing Mentions Parsing...")
try:
    # Parse mentions
    m_res = requests.post(f"{API_URL}/api/mentions/parse", json={
        "room_id": room_id,
        "message_text": "Need help on liability limits @ForgeBot and @John",
        "author_id": user_id
    }, headers=auth_headers)
    print(f"Mentions Parse Status: {m_res.status_code}")
    assert m_res.status_code == 200, "Parse mentions failed"
    parsed_mentions = m_res.json()["mentions"]
    print(f"✓ Extracted Mentions: {', '.join([m['mentioned_username'] for m in parsed_mentions])}")
except Exception as e:
    print(f"❌ Mentions Parse Error: {e}")
    sys.exit(1)

print("\n[13/14] Testing Smart Summarization...")
try:
    # Summarize transcript
    sum_res = requests.post(f"{API_URL}/api/rooms/{room_id}/summarize", headers=auth_headers)
    print(f"Summarize Status: {sum_res.status_code}")
    assert sum_res.status_code == 200, "Summarize failed"
    sum_data = sum_res.json()
    print(f"✓ Extracted Overview: '{sum_data['summary']['summary']}'")
    print(f"✓ Markdown Summary length: {len(sum_data['markdown'])} chars")
except Exception as e:
    print(f"❌ Summarization Error: {e}")
    sys.exit(1)

print("\n[14/14] Testing Emoji Reactions Feedback...")
try:
    # Get outputs
    room_detail_res = requests.get(f"{API_URL}/api/rooms/{room_id}", headers=auth_headers)
    room_detail = room_detail_res.json()
    outputs = room_detail.get("outputs", [])
    if outputs:
        card_id = outputs[0].get("id") or outputs[0].get("_id")
        
        # Add feedback rating
        f_res = requests.post(f"{API_URL}/api/outputs/{card_id}/feedback", json={
            "room_id": room_id,
            "user_id": user_id,
            "feedback_type": "thumbs_up"
        }, headers=auth_headers)
        print(f"Add Feedback Status: {f_res.status_code}")
        assert f_res.status_code == 200, "Recording feedback rating failed"
        
        # Add emoji reaction
        e_res = requests.post(f"{API_URL}/api/outputs/{card_id}/feedback", json={
            "room_id": room_id,
            "user_id": user_id,
            "feedback_type": "emoji",
            "emoji": "😍"
        }, headers=auth_headers)
        print(f"Add Emoji Status: {e_res.status_code}")
        assert e_res.status_code == 200, "Recording emoji reaction failed"
        
        # Retrieve summary
        f_sum_res = requests.get(f"{API_URL}/api/outputs/{card_id}/feedback", headers=auth_headers)
        f_sum_data = f_sum_res.json()
        print(f"✓ Thumbs-up Count: {f_sum_data['thumbs_up_count']}, Quality: {int(f_sum_data['quality_score']*100)}%")
        assert f_sum_data["thumbs_up_count"] == 1, "Incorrect thumbs count"
    else:
         print("⚠ No output cards in room to rate. Skipping reactions test.")
except Exception as e:
    print(f"❌ Feedback Reactions Error: {e}")
    sys.exit(1)

print("\n🎉 ALL 14 FORGEROOM MVP + ADVANCED INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
print("Everything works end-to-end (Auth, Database seeding, NVIDIA Streaming, snapshots, branching, templates, summarize, and feedback reactions).")
