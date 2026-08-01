import re
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.database import get_db
from app.models.advanced import (
    MentionResponse,
    MentionInDB,
    MentionNotificationInDB,
    MentionNotificationResponse
)
from bson import ObjectId

router = APIRouter(prefix="/mentions", tags=["mentions"])
logger = logging.getLogger("uvicorn")

@router.post("/parse")
async def parse_mentions(data: dict):
    """
    Parse a message string for @mentions and extract target metadata.
    data = {
        "room_id": str,
        "message_text": str,
        "author_id": str
    }
    """
    message_text = data.get("message_text", "")
    room_id = data.get("room_id")
    
    # regex matches alphanumeric words prefixed with @
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, message_text)
    
    db = get_db()
    
    # Fetch active online/offline members to match username
    participants_cursor = db["room_participants"].find({"room_id": room_id})
    participants = await participants_cursor.to_list(length=100)
    participant_names = {p["username"].lower(): str(p["user_id"]) for p in participants}
    
    stored_mentions = []
    for mention in mentions:
        m_lower = mention.lower()
        mention_type = "agent" if m_lower in ["forgebot", "agent", "ai", "claude"] else "user"
        
        mentioned_user_id = participant_names.get(m_lower)
        
        if mentioned_user_id or mention_type == "agent":
            stored_mentions.append({
                "room_id": room_id,
                "mentioned_username": mention,
                "mentioned_user_id": mentioned_user_id,
                "mention_type": mention_type
            })
            
    return {"mentions": stored_mentions, "count": len(stored_mentions)}

@router.post("/messages/{message_id}")
async def save_message_mentions(message_id: str, data: dict):
    """Save all mentions associated with a message and insert notifications"""
    mentions = data.get("mentions", [])
    db = get_db()
    
    saved_count = 0
    for mention in mentions:
        # Create mention entry
        m_db = MentionInDB(
            room_id=mention["room_id"],
            message_id=message_id,
            mentioned_user_id=mention.get("mentioned_user_id"),
            mentioned_username=mention["mentioned_username"],
            mention_type=mention["mention_type"]
        )
        m_result = await db["mentions"].insert_one(m_db.model_dump(by_alias=True, exclude=["id"]))
        saved_count += 1
        
        # If user mention, create unread notification card
        target_user = mention.get("mentioned_user_id")
        if target_user and mention["mention_type"] == "user":
            n_db = MentionNotificationInDB(
                user_id=target_user,
                mention_id=str(m_result.inserted_id),
                is_read=False
            )
            await db["mention_notifications"].insert_one(n_db.model_dump(by_alias=True, exclude=["id"]))
            
    return {"mentions_saved": saved_count}

@router.get("/users/{user_id}/unread")
async def get_unread_mentions(user_id: str):
    """Get unread notifications lists for user"""
    db = get_db()
    cursor = db["mention_notifications"].find({"user_id": user_id, "is_read": False}).sort("created_at", -1)
    notifications = await cursor.to_list(length=100)
    
    # Load detailed mention bodies
    enriched = []
    for n in notifications:
        m_id = n["mention_id"]
        mention = await db["mentions"].find_one({"_id": ObjectId(m_id)})
        if mention:
            enriched.append({
                "notification_id": str(n["_id"]),
                "room_id": mention["room_id"],
                "message_id": mention["message_id"],
                "mentioned_username": mention["mentioned_username"],
                "created_at": n["created_at"]
            })
            
    return {"unread_count": len(enriched), "mentions": enriched}

@router.post("/{notification_id}/read")
async def mark_mention_read(notification_id: str):
    """Mark a mention notification as read"""
    db = get_db()
    try:
        await db["mention_notifications"].update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"is_read": True}}
        )
        return {"status": "read"}
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Invalid notification ID format: {e}")
