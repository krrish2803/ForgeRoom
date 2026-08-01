import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, get_db
from app.auth.routes import router as auth_router
from app.rooms.routes import router as rooms_router
from app.agent.routes import router as agent_router
from app.export.routes import router as export_router
from app.websocket.manager import manager
from app.models.message import MessageInDB
from app.agent.routes import agent_respond
from app.mentions.routes import router as mentions_router
from app.templates.routes import router as templates_router
from app.feedback.routes import router as feedback_router
from app.orgs.routes import router as orgs_router
from app.agent_custom.routes import router as custom_agent_router
from app.agent.research import router as research_router
import jwt
from jwt.exceptions import PyJWTError
from datetime import datetime

logger = logging.getLogger("uvicorn")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title="ForgeRoom MVP API",
    description="Multiplayer AI Agent Workspace MVP Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix="/api")
app.include_router(rooms_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(custom_agent_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(mentions_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(orgs_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# ==========================================
# MULTIPLAYER WEBSOCKET SYSTEM
# ==========================================
@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(...)
):
    db = get_db()
    
    # 1. JWT Authentication check
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    user_doc = await db["users"].find_one({"_id": user_id})
    if not user_doc:
        # Check guest fallback
        # If user_id starts with a string UUID, we check if it is stored in users
        from bson import ObjectId
        try:
            user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
        except Exception:
            user_doc = None
            
        if not user_doc:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    user_name = user_doc["name"]
    
    # 2. Confirm room exists
    room_doc = await db["rooms"].find_one({"_id": room_id})
    if not room_doc:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    org_id = room_doc.get("org_id")
    user_role = "owner"  # Default for personal rooms
    if org_id:
        member = await db["org_members"].find_one({"org_id": org_id, "user_id": user_id})
        if not member:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_role = member["role"]
        
    # Mark participant as online in DB
    await db["room_participants"].update_one(
        {"room_id": room_id, "user_id": user_id},
        {
            "$set": {
                "room_id": room_id,
                "user_id": user_id,
                "username": user_name,
                "avatar_initial": user_name[0].upper() if user_name else "G",
                "is_online": True,
                "last_seen": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    # Connect client
    await manager.connect(websocket, room_id, user_name)
    
    # Log audit entry for room joining
    if org_id:
        from app.orgs.routes import log_org_action
        await log_org_action(
            db, org_id, user_id, user_name,
            "room_joined", f"User '{user_name}' joined active session room.",
            room_id=room_id
        )
    
    try:
        while True:
            # Listen to messages
            data = await websocket.receive_json()
            message_text = data.get("content", "").strip()
            
            if not message_text:
                continue
                
            # Block viewers from broadcasting messages
            if user_role == "viewer":
                await websocket.send_json({
                    "type": "error",
                    "content": "Read-only: Users with 'Viewer' role cannot post chat messages."
                })
                continue
                
            # Create message payload in database
            msg_db = MessageInDB(
                room_id=room_id,
                user_id=user_id,
                username=user_name,
                content=message_text,
                message_type="user"
            )
            result = await db["messages"].insert_one(msg_db.model_dump(by_alias=True, exclude=["id"]))
            
            # Broadcast user message to room
            broadcast_msg = {
                "type": "message",
                "id": str(result.inserted_id),
                "room_id": room_id,
                "user_id": user_id,
                "username": user_name,
                "content": message_text,
                "message_type": "user",
                "timestamp": datetime.utcnow().isoformat()
            }
            await manager.broadcast_to_room(room_id, broadcast_msg)
            
            # If user message tags @ForgeBot, trigger agent respond
            if "@forgebot" in message_text.lower():
                # We can call the agent respond routine in the background
                import asyncio
                asyncio.create_task(trigger_agent_respond_flow(room_id, str(result.inserted_id), message_text))
                
    except WebSocketDisconnect:
        # Mark participant as offline
        await db["room_participants"].update_one(
            {"room_id": room_id, "user_id": user_id},
            {"$set": {"is_online": False, "last_seen": datetime.utcnow()}}
        )
        await manager.disconnect(websocket, room_id, user_name)
    except Exception as e:
        logger.error(f"WebSocket error in room {room_id}: {e}")
        await manager.disconnect(websocket, room_id, user_name)

async def trigger_agent_respond_flow(room_id: str, message_id: str, user_message: str):
    """Trigger agent response helper for WebSocket actions"""
    try:
        payload = {
            "room_id": room_id,
            "message_id": message_id,
            "user_message": user_message,
            "conversation_history": []
        }
        # Call the agent respond route logic internally
        async for chunk in (await agent_respond(payload)).body_iterator:
            pass # The agent respond endpoint automatically broadcasts tokens over WebSockets!
    except Exception as e:
        logger.error(f"Error in automatic socket agent response flow: {e}")

# Mount static files (HTML, JS, CSS) from the parent directory of backend
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
