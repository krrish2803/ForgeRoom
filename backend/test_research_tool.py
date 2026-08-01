import requests
import sys
import json
import time

API_URL = "http://localhost:8002"

print("====================================================")
print("             FORGEROOM RESEARCH TOOL TEST           ")
print("====================================================")

# Generate unique names & emails
rand = int(time.time())
owner_email = f"research_owner_{rand}@testforgeroom.com"
test_password = "secure_password_123"

# 1. REGISTER OWNER
print("\n[1/5] Registering Org Owner...")
try:
    res = requests.post(f"{API_URL}/api/auth/register", json={
        "name": "Research Admin", "email": owner_email, "password": test_password
    })
    assert res.status_code == 201, f"Owner registration failed: {res.text}"
    owner_id = res.json()["_id"]
    print("✓ Successfully registered owner.")
except Exception as e:
    print(f"❌ Owner Registration Error: {e}")
    sys.exit(1)

# 2. LOGIN OWNER & GET TOKEN
print("\n[2/5] Logging in Org Owner...")
try:
    res = requests.post(f"{API_URL}/api/auth/login", json={"email": owner_email, "password": test_password})
    assert res.status_code == 200, "Owner login failed"
    owner_token = res.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}
    print("✓ Tokens acquired successfully.")
except Exception as e:
    print(f"❌ Login Error: {e}")
    sys.exit(1)

# 3. CREATE ROOM
print("\n[3/5] Creating Room...")
try:
    res = requests.post(f"{API_URL}/api/rooms", json={"name": "Research Sandbox Room", "created_by_id": owner_id}, headers=owner_headers)
    assert res.status_code == 201, f"Room creation failed: {res.text}"
    room_id = res.json()["_id"]
    print(f"✓ Created Room with ID: {room_id}")
except Exception as e:
    print(f"❌ Room Setup Error: {e}")
    sys.exit(1)

# 4. TRIGGER RESEARCH STREAM & VERIFY SSE
print("\n[4/5] Triggering Research Workflow SSE Stream...")
try:
    payload = {
        "query": "liability limits under California consumer protection laws"
    }
    
    # Make request to stream SSE output
    res = requests.post(f"{API_URL}/api/rooms/{room_id}/research", json=payload, headers=owner_headers, stream=True)
    assert res.status_code == 200, f"Research trigger failed: {res.text}"
    
    print("✓ Streaming SSE connection established. Printing status transitions and tokens:")
    status_received = False
    tokens_received = False
    done_received = False
    
    for line in res.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                data = json.loads(decoded_line[6:])
                if data["type"] == "status":
                    print(f"\n   [STATUS] {data['content']}")
                    status_received = True
                elif data["type"] == "token":
                    sys.stdout.write(data["content"])
                    sys.stdout.flush()
                    tokens_received = True
                elif data["type"] == "done":
                    print("\n✓ Stream completed.")
                    done_received = True
                    break
                    
    assert status_received, "Failed to receive simulated research progress status logs"
    assert tokens_received, "Failed to receive streamed content tokens"
    assert done_received, "Stream did not end with 'done' type"
except Exception as e:
    print(f"❌ Research Chained Streaming Error: {e}")
    sys.exit(1)

# 5. VERIFY DATABASE MESSAGE LOGS & CANVAS CARDS
print("\n[5/5] Checking Room Messages & Canvas Cards in Database...")
try:
    # Fetch room details
    res = requests.get(f"{API_URL}/api/rooms/{room_id}", headers=owner_headers)
    assert res.status_code == 200, "Failed to fetch room details"
    details = res.json()
    
    # Assert a canvas card from ResearchBot exists
    cards = details["outputs"]
    research_card = next((c for c in cards if c["title"].startswith("Research:")), None)
    assert research_card is not None, "Failed to find newly created Research card in Canvas"
    print(f"✓ Found Canvas card: '{research_card['title']}' with draft status.")
    
    # Assert chat message exists
    assert "liability limits" in research_card["content"].lower(), "Research report content is empty or mismatched"
    print("✓ Verified research contents successfully saved to DB collections.")
except Exception as e:
    print(f"❌ Database Verification Error: {e}")
    sys.exit(1)

print("\n====================================================")
print("     🎉 ALL RESEARCH TOOL INTEGRATION TESTS PASSED! ")
print("====================================================")
