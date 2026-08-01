import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.database import get_db
from app.websocket.manager import manager
from app.models.advanced import FeedbackSummaryResponse
from bson import ObjectId

router = APIRouter(prefix="/outputs/{output_id}/feedback", tags=["feedback"])
logger = logging.getLogger("uvicorn")

@router.post("")
async def add_feedback(output_id: str, data: dict):
    """
    Add feedback rating or emoji reaction to an agent output card.
    Calculates dynamic summaries and broadcasts updates.
    data = {
        "room_id": str,
        "user_id": str,
        "feedback_type": str, # "thumbs_up" | "thumbs_down" | "emoji"
        "emoji": str (optional),
        "comment": str (optional)
    }
    """
    room_id = data.get("room_id")
    user_id = data["user_id"]
    feedback_type = data["feedback_type"]
    
    db = get_db()
    
    # 1. Upsert individual feedback record (Unique per user + output + feedback_type combo)
    f_record = {
        "output_id": output_id,
        "room_id": room_id,
        "user_id": user_id,
        "feedback_type": feedback_type,
        "emoji": data.get("emoji"),
        "comment": data.get("comment"),
        "created_at": datetime.utcnow()
    }
    
    await db["feedback"].update_one(
        {"output_id": output_id, "user_id": user_id, "feedback_type": feedback_type},
        {"$set": f_record},
        upsert=True
    )
    
    # 2. Recalculate summary totals
    feedback_cursor = db["feedback"].find({"output_id": output_id})
    all_feedback = await feedback_cursor.to_list(length=1000)
    
    thumbs_up = len([f for f in all_feedback if f["feedback_type"] == "thumbs_up"])
    thumbs_down = len([f for f in all_feedback if f["feedback_type"] == "thumbs_down"])
    
    emoji_reactions = {}
    for f in all_feedback:
        if f["feedback_type"] == "emoji" and f.get("emoji"):
            emoji = f["emoji"]
            emoji_reactions[emoji] = emoji_reactions.get(emoji, 0) + 1
            
    total = thumbs_up + thumbs_down
    quality_score = (thumbs_up / total) if total > 0 else 0.5
    
    # Update Feedback Summary in Database
    summary_db = {
        "output_id": output_id,
        "thumbs_up_count": thumbs_up,
        "thumbs_down_count": thumbs_down,
        "emoji_reactions": emoji_reactions,
        "quality_score": quality_score
    }
    
    await db["feedback_summary"].update_one(
        {"output_id": output_id},
        {"$set": summary_db},
        upsert=True
    )
    
    # Get the inserted summary with ObjectId
    summary_doc = await db["feedback_summary"].find_one({"output_id": output_id})
    summary_doc["id"] = str(summary_doc["_id"])
    if "_id" in summary_doc:
        del summary_doc["_id"]
    
    # 3. Broadcast update over WebSocket to room
    await manager.broadcast_to_room(room_id, {
        "type": "feedback_update",
        "output_id": output_id,
        "thumbs_up_count": thumbs_up,
        "thumbs_down_count": thumbs_down,
        "emoji_reactions": emoji_reactions,
        "quality_score": quality_score
    })
    
    return {"status": "feedback recorded", "summary": summary_doc}

@router.get("")
async def get_feedback_summary(output_id: str):
    """Retrieve aggregate feedback details for a specific card"""
    db = get_db()
    summary = await db["feedback_summary"].find_one({"output_id": output_id})
    if not summary:
        return {
            "output_id": output_id,
            "thumbs_up_count": 0,
            "thumbs_down_count": 0,
            "emoji_reactions": {},
            "quality_score": 0.5
        }
    summary["id"] = str(summary["_id"])
    if "_id" in summary:
        del summary["_id"]
    return summary
