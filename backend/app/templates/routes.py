import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.database import get_db
from app.models.advanced import TemplateResponse, TemplateInDB
from app.models.room import RoomResponse, RoomInDB

router = APIRouter(prefix="/templates", tags=["templates"])

@router.get("", response_model=dict)
async def list_templates():
    """Get all seeded Magic Templates"""
    db = get_db()
    cursor = db["templates"].find()
    templates = await cursor.to_list(length=100)
    
    # Map _id back to id or populate alias
    out = []
    for t in templates:
        t_id = t.get("_id")
        t["id"] = t_id
        out.append(t)
    return {"templates": out}

@router.post("/{template_slug}/create-room")
async def create_room_from_template(template_slug: str, data: dict):
    """
    Create a new room pre-configured with a Magic Template's context.
    data = {
        "created_by_id": str,
        "custom_name": str (optional)
    }
    """
    db = get_db()
    
    # 1. Fetch template context
    template = await db["templates"].find_one({"_id": template_slug})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    room_name = data.get("custom_name", template["name"])
    created_by = data["created_by_id"]
    
    room_id = str(uuid.uuid4())
    
    # 2. Insert Room with template starter metadata
    room_db = RoomInDB(
        _id=room_id,
        name=room_name,
        created_by=created_by,
        is_public=True,
        contract_text=None,
        metadata={
            "template_used": template_slug,
            "starter_prompt": template["starter_prompt"],
            "suggested_agents": template.get("suggested_agents", [])
        }
    )
    await db["rooms"].insert_one(room_db.model_dump(by_alias=True))
    
    # 3. Add initial welcome banner message
    welcome_msg = {
        "room_id": room_id,
        "user_id": "system",
        "username": "System",
        "content": f"🎯 Workspace created using template: **{template['name']}**\n\n_{template['description']}_\n\n*Suggested Roles*: {', '.join(template.get('suggested_agents', []))}",
        "message_type": "agent",
        "created_at": datetime.utcnow()
    }
    await db["messages"].insert_one(welcome_msg)
    
    return {
        "room_id": room_id,
        "template": template,
        "url": f"/room/{room_id}"
    }
