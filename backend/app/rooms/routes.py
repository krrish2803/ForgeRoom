import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.auth.security import get_current_user
from app.models.user import UserInDB
from app.orgs.routes import get_org_member_role
from app.models.room import (
    RoomCreate,
    RoomResponse,
    RoomInDB,
    ParticipantResponse,
    ParticipantInDB,
    AgentOutputResponse,
    SessionVersionResponse,
    SessionVersionInDB
)
from app.models.message import MessageResponse, VersionMessageInDB

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(data: RoomCreate):
    """Create a new room. data = {name, created_by_id, org_id}"""
    db = get_db()
    
    # Verify creator has Owner/Editor permissions if Org room
    if data.org_id:
        from bson import ObjectId
        member = await db["org_members"].find_one({"org_id": data.org_id, "user_id": data.created_by_id})
        if not member or member["role"] not in ["owner", "editor"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization Owners or Editors can create rooms"
            )
            
    room_id = str(uuid.uuid4())
    
    room_db = RoomInDB(
        _id=room_id,
        name=data.name,
        created_by=data.created_by_id,
        org_id=data.org_id,
        is_public=True,
        contract_text=None,
        metadata={}
    )
    
    try:
        await db["rooms"].insert_one(room_db.model_dump(by_alias=True))
        
        # Log to Audit log
        if data.org_id:
            from bson import ObjectId
            user_doc = await db["users"].find_one({"_id": ObjectId(data.created_by_id)})
            username = user_doc["name"] if user_doc else "Unknown"
            from app.orgs.routes import log_org_action
            await log_org_action(
                db, data.org_id, data.created_by_id, username,
                "room_created", f"Collaborative Room '{data.name}' was created.",
                room_id=room_id
            )
            
        room_doc = await db["rooms"].find_one({"_id": room_id})
        # Defensive schema compatibility checks
        if "title" in room_doc and "name" not in room_doc:
            room_doc["name"] = room_doc["title"]
        if "owner_id" in room_doc and "created_by" not in room_doc:
            room_doc["created_by"] = room_doc["owner_id"]
        return RoomResponse(**room_doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list", response_model=List[RoomResponse])
async def list_rooms(org_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user)):
    """Get list of collaborative rooms, optionally filtered by Org"""
    db = get_db()
    
    query = {}
    if org_id:
        # Verify user is member of organization
        await get_org_member_role(db, org_id, str(current_user.id))
        query["org_id"] = org_id
    else:
        # Personal rooms have no org_id or empty string
        query["org_id"] = {"$in": [None, ""]}
        
    cursor = db["rooms"].find(query)
    rooms = await cursor.to_list(length=100)
    
    sanitized = []
    for r in rooms:
        if "title" in r and "name" not in r:
            r["name"] = r["title"]
        if "owner_id" in r and "created_by" not in r:
            r["created_by"] = r["owner_id"]
        if "created_at" not in r:
            r["created_at"] = datetime.utcnow()
        sanitized.append(r)
        
    return sanitized

@router.get("/{room_id}")
async def get_room(room_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Fetch room details, participants list, canvas outputs, and current user's role"""
    db = get_db()
    
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if "title" in room and "name" not in room:
        room["name"] = room["title"]
    if "owner_id" in room and "created_by" not in room:
        room["created_by"] = room["owner_id"]
    if "created_at" not in room:
        room["created_at"] = datetime.utcnow()
        
    # Check Org membership if room belongs to Org
    org_id = room.get("org_id")
    user_role = "owner"  # Default for personal room
    if org_id:
        member = await db["org_members"].find_one({"org_id": org_id, "user_id": str(current_user.id)})
        if not member:
            raise HTTPException(status_code=403, detail="You are not a member of this organization")
        user_role = member["role"]
        
    participants_cursor = db["room_participants"].find({"room_id": room_id, "is_online": True})
    participants = await participants_cursor.to_list(length=100)
    
    outputs_cursor = db["agent_outputs"].find({"room_id": room_id})
    outputs = await outputs_cursor.to_list(length=100)
    
    return {
        "room": RoomResponse(**room),
        "participants": [ParticipantResponse(**p) for p in participants],
        "outputs": [AgentOutputResponse(**o) for o in outputs],
        "user_role": user_role
    }

@router.delete("/{room_id}")
async def delete_room(room_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Delete a room and all associated data"""
    db = get_db()
    
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check permissions: room creator or org owner/editor can delete
    user_id = str(current_user.id)
    is_creator = room.get("created_by") == user_id
    
    org_id = room.get("org_id")
    if org_id:
        role = await get_org_member_role(db, org_id, user_id)
        if not is_creator and role not in ["owner", "editor"]:
            raise HTTPException(status_code=403, detail="Only room creator or organization owner/editor can delete rooms")
    elif not is_creator:
        raise HTTPException(status_code=403, detail="Only room creator can delete rooms")
    
    # Delete all related data
    await db["room_participants"].delete_many({"room_id": room_id})
    await db["messages"].delete_many({"room_id": room_id})
    await db["agent_outputs"].delete_many({"room_id": room_id})
    await db["session_versions"].delete_many({"room_id": room_id})
    await db["version_messages"].delete_many({"room_id": room_id})
    await db["rooms"].delete_one({"_id": room_id})
    
    # Audit log
    if org_id:
        from app.orgs.routes import log_org_action
        await log_org_action(
            db, org_id, user_id, current_user.name,
            "room_deleted", f"Deleted room '{room.get('name')}'.",
            room_id=room_id
        )
    
    return {"status": "deleted", "room_id": room_id}

@router.post("/{room_id}/workflow")
async def update_room_workflow(room_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Set active agent or active chain workflow for a room"""
    db = get_db()
    
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    org_id = room.get("org_id")
    if org_id:
        role = await get_org_member_role(db, org_id, str(current_user.id))
        if role not in ["owner", "editor"]:
            raise HTTPException(status_code=403, detail="Viewer role cannot update room settings")
            
    active_agent_id = data.get("active_agent_id")
    active_chain_id = data.get("active_chain_id")
    
    await db["rooms"].update_one(
        {"_id": room_id},
        {"$set": {
            "active_agent_id": active_agent_id if active_agent_id else None,
            "active_chain_id": active_chain_id if active_chain_id else None
        }}
    )
    
    # Audit log
    if org_id:
        from app.orgs.routes import log_org_action
        workflow_label = f"Agent: '{active_agent_id}'" if active_agent_id else (f"Chain: '{active_chain_id}'" if active_chain_id else "Default Agent")
        await log_org_action(
            db, org_id, str(current_user.id), current_user.name,
            "room_workflow_updated", f"Updated room active pipeline workflow to {workflow_label}.",
            room_id=room_id
        )
        
    return {"status": "success", "active_agent_id": active_agent_id, "active_chain_id": active_chain_id}

@router.post("/{room_id}/join")
async def join_room(room_id: str, data: dict):
    """Join a room. data = {user_id, username}"""
    db = get_db()
    user_id = data["user_id"]
    username = data["username"]
    
    participant = {
        "room_id": room_id,
        "user_id": user_id,
        "username": username,
        "avatar_initial": username[0].upper() if username else "G",
        "joined_at": datetime.utcnow(),
        "last_seen": datetime.utcnow(),
        "is_online": True
    }
    
    try:
        await db["room_participants"].update_one(
            {"room_id": room_id, "user_id": user_id},
            {"$set": participant},
            upsert=True
        )
        
        # Broadcast presence list update via WebSocket manager (implemented in main.py WebSocket endpoint)
        from app.websocket.manager import manager
        await manager.broadcast_presence(room_id)
        
        return {"status": "joined"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{room_id}/leave")
async def leave_room(room_id: str, data: dict):
    """User leaves the room"""
    db = get_db()
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
        
    await db["room_participants"].update_one(
        {"room_id": room_id, "user_id": user_id},
        {"$set": {"is_online": False, "last_seen": datetime.utcnow()}}
    )
    
    from app.websocket.manager import manager
    await manager.broadcast_presence(room_id)
    
    return {"status": "left"}

@router.post("/{room_id}/upload-contract")
async def upload_contract(room_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Save contract clause text in room"""
    db = get_db()
    
    # Fetch Room and verify Org scope
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    org_id = room.get("org_id")
    if org_id:
        role = await get_org_member_role(db, org_id, str(current_user.id))
        if role == "viewer":
            raise HTTPException(status_code=403, detail="Viewer role cannot upload contract clauses")
            
    contract_text = data.get("contract_text", "")
    
    await db["rooms"].update_one(
        {"_id": room_id},
        {"$set": {"contract_text": contract_text}}
    )
    
    # Log to Audit trail
    if org_id:
        from app.orgs.routes import log_org_action
        await log_org_action(
            db, org_id, str(current_user.id), current_user.name,
            "contract_uploaded", "Uploaded contract clause text.",
            room_id=room_id
        )
        
    return {"status": "uploaded", "contract_text": contract_text}

# ==========================================
# SNAPSHOT & VERSIONING ENDPOINTS
# ==========================================
@router.post("/{room_id}/versions")
async def save_version(room_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Save current room transcript as a snapshot version"""
    db = get_db()
    
    # Verify Org scope
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    org_id = room.get("org_id")
    if org_id:
        role = await get_org_member_role(db, org_id, str(current_user.id))
        if role == "viewer":
            raise HTTPException(status_code=403, detail="Viewer role cannot create snapshots")
            
    user_id = str(current_user.id)
    label = data.get("label", "")
    
    # Get latest version number
    latest = await db["session_versions"].find_one(
        {"room_id": room_id},
        sort=[("version_number", -1)]
    )
    next_version = (latest["version_number"] + 1) if latest else 1
    if not label:
        label = f"Version {next_version}"
        
    version_id = str(uuid.uuid4())
    version_db = SessionVersionInDB(
        _id=version_id,
        room_id=room_id,
        version_number=next_version,
        label=label,
        created_by=user_id
    )
    
    # Save version record
    await db["session_versions"].insert_one(version_db.model_dump(by_alias=True))
    
    # Audit trail
    if org_id:
        from app.orgs.routes import log_org_action
        await log_org_action(
            db, org_id, str(current_user.id), current_user.name,
            "version_created", f"Created room transcript snapshot: '{label}' (v{next_version}).",
            room_id=room_id
        )
    
    # Snapshot current messages
    messages_cursor = db["messages"].find({"room_id": room_id})
    messages = await messages_cursor.to_list(length=1000)
    
    version_messages = []
    for msg in messages:
        v_msg = VersionMessageInDB(
            version_id=version_id,
            message_id=str(msg["_id"]),
            room_id=room_id,
            content=msg["content"],
            message_type=msg["message_type"],
            username=msg["username"],
            created_at=msg["created_at"]
        )
        version_messages.append(v_msg.model_dump(by_alias=True, exclude=["id"]))
        
    if version_messages:
        await db["version_messages"].insert_many(version_messages)
        
    return {"version_id": version_id, "version_number": next_version}

@router.get("/{room_id}/versions")
async def list_versions(room_id: str):
    """List all version snapshots of this room"""
    db = get_db()
    cursor = db["session_versions"].find({"room_id": room_id}).sort("version_number", 1)
    versions = await cursor.to_list(length=100)
    return {"versions": [SessionVersionResponse(**v) for v in versions]}

@router.post("/{room_id}/versions/{version_id}/branch")
async def branch_from_version(room_id: str, version_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Branch from a version: create a new room with cloned transcript history"""
    db = get_db()
    
    # Get old room's details to copy and check Org scope
    old_room = await db["rooms"].find_one({"_id": room_id})
    if not old_room:
        raise HTTPException(status_code=404, detail="Source Room not found")
        
    org_id = old_room.get("org_id")
    if org_id:
        role = await get_org_member_role(db, org_id, str(current_user.id))
        if role == "viewer":
            raise HTTPException(status_code=403, detail="Viewer role cannot branch rooms")
            
    user_id = str(current_user.id)
    branch_name = data.get("name", f"Branch from v_{version_id[:8]}")
    
    # Verify version snapshot exists
    version_rec = await db["session_versions"].find_one({"_id": version_id})
    if not version_rec:
        raise HTTPException(status_code=404, detail="Version snapshot not found")
        
    cursor = db["version_messages"].find({"version_id": version_id})
    v_messages = await cursor.to_list(length=1000)
    
    contract_text = old_room.get("contract_text")
    
    # Create new branched room under the same Org
    new_room_id = str(uuid.uuid4())
    new_room = RoomInDB(
        _id=new_room_id,
        name=branch_name,
        created_by=user_id,
        org_id=org_id,
        is_public=True,
        contract_text=contract_text,
        metadata={"branched_from": room_id, "version_id": version_id}
    )
    await db["rooms"].insert_one(new_room.model_dump(by_alias=True))
    
    # Log to Audit trail
    if org_id:
        from app.orgs.routes import log_org_action
        await log_org_action(
            db, org_id, str(current_user.id), current_user.name,
            "room_branched", f"Branched workspace room '{branch_name}' from version snapshot '{version_id[:8]}'.",
            room_id=new_room_id
        )
    
    # Copy cloned message transcript
    cloned_messages = []
    for msg in v_messages:
        cloned_messages.append({
            "room_id": new_room_id,
            "user_id": "system",
            "username": msg["username"],
            "content": msg["content"],
            "message_type": msg["message_type"],
            "created_at": datetime.utcnow()
        })
        
    if cloned_messages:
        await db["messages"].insert_many(cloned_messages)
        
    return {"new_room_id": new_room_id}

@router.patch("/{room_id}/outputs/{output_id}")
async def update_agent_output(room_id: str, output_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Update title, content, or status of an agent output card"""
    db = get_db()
    from bson import ObjectId
    
    # Check Org scope
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    org_id = room.get("org_id")
    if org_id:
        role = await get_org_member_role(db, org_id, str(current_user.id))
        if role == "viewer":
            raise HTTPException(status_code=403, detail="Viewer role cannot modify canvas items")
            
    update_data = {}
    if "content" in data:
        update_data["content"] = data["content"]
    if "status" in data:
        update_data["status"] = data["status"]
    if "title" in data:
        update_data["title"] = data["title"]
        
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
        
    update_data["edited_at"] = datetime.utcnow()
    
    result = await db["agent_outputs"].update_one(
        {"_id": ObjectId(output_id), "room_id": room_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Canvas output card not found")
        
    card_doc = await db["agent_outputs"].find_one({"_id": ObjectId(output_id)})
    if card_doc:
        card_doc["id"] = str(card_doc["_id"])
        if "_id" in card_doc:
            del card_doc["_id"]
        if "created_at" in card_doc:
             card_doc["created_at"] = card_doc["created_at"].isoformat()
        if "edited_at" in card_doc:
             card_doc["edited_at"] = card_doc["edited_at"].isoformat()
             
        # Log to audit trail
        if org_id:
            from app.orgs.routes import log_org_action
            action_desc = "card_edited"
            details_desc = f"Edited card: '{card_doc.get('title')}'."
            if "status" in data:
                action_desc = "card_finalized" if data["status"] == "finalized" else "card_reopened"
                details_desc = f"Changed card status to '{data['status']}': '{card_doc.get('title')}'."
            await log_org_action(
                db, org_id, str(current_user.id), current_user.name,
                action_desc, details_desc,
                room_id=room_id
            )
             
        from app.websocket.manager import manager
        await manager.broadcast_to_room(room_id, {
            "type": "card_update_broadcast",
            "output": card_doc
        })
        
    return {"status": "updated"}

@router.post("/{room_id}/add-member")
async def add_member_to_room(room_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Add a member to the room by user email"""
    db = get_db()
    
    # Check Org scope: Only Owner can add room participants
    room = await db["rooms"].find_one({"_id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    org_id = room.get("org_id")
    if org_id:
        role = await get_org_member_role(db, org_id, str(current_user.id))
        if role != "owner":
            raise HTTPException(status_code=403, detail="Only organization Owners can invite members to room workspaces")
            
    email = data.get("user_email")
    if not email:
        raise HTTPException(status_code=400, detail="user_email is required")
        
    # Check if user exists
    user = await db["users"].find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail=f"User with email '{email}' not found")
        
    # Add to room_participants (offline by default, until they join)
    participant = {
        "room_id": room_id,
        "user_id": str(user["_id"]),
        "username": user["name"],
        "avatar_initial": user["name"][0].upper() if user.get("name") else "U",
        "joined_at": datetime.utcnow(),
        "last_seen": datetime.utcnow(),
        "is_online": False  # Will turn True when they connect via WS
    }
    
    await db["room_participants"].update_one(
        {"room_id": room_id, "user_id": str(user["_id"])},
        {"$set": participant},
        upsert=True
    )
    
    # Log to audit trail
    if org_id:
        from app.orgs.routes import log_org_action
        await log_org_action(
            db, org_id, str(current_user.id), current_user.name,
            "room_member_added", f"Added user '{user['name']}' to active workspace room.",
            room_id=room_id
        )
        
    return {"status": "member invited", "username": user["name"]}

