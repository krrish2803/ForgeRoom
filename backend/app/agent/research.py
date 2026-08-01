import json
import logging
import asyncio
import httpx
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from app.config import settings
from app.database import get_db
from app.auth.security import get_current_user
from app.models.user import UserInDB
from app.agent.nvidia import nvidia_client
from app.websocket.manager import manager
from bson import ObjectId

router = APIRouter(prefix="/rooms", tags=["research"])
logger = logging.getLogger("uvicorn")

async def search_tavily(query: str) -> dict:
    """Helper connecting to Tavily Search API to execute real-time web search"""
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY environment variable is missing. Graceful mock fallback.")
        return {"results": []}

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.tavily.com/search",
                json=payload,
                timeout=20.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying Tavily Search API: {e}")
            return {"results": []}

@router.post("/{room_id}/research")
async def trigger_room_research(
    room_id: str,
    data: dict,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Triggers Tavily Live Search research workflow and streams LLM output.
    data = { "query": str }
    """
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
        
    db = get_db()
    room_doc = await db["rooms"].find_one({"_id": room_id})
    if not room_doc:
        raise HTTPException(status_code=404, detail="Room not found")
        
    # Check permissions
    org_id = room_doc.get("org_id")
    if org_id:
        member = await db["org_members"].find_one({"org_id": org_id, "user_id": str(current_user.id)})
        if not member or member["role"] == "viewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewer role cannot trigger research lookups"
            )
            
    contract = room_doc.get("contract_text", "No contract loaded yet.")

    async def research_event_generator():
        # Step 1: Broadcasting Status 1 & Triggering Tavily Search
        status_msg = f"🔍 Searching the web via Tavily for: '{query}'..."
        await manager.broadcast_to_room(room_id, {
            "type": "research_status",
            "content": status_msg
        })
        yield f"data: {json.dumps({'type': 'status', 'content': status_msg})}\n\n"
        
        tavily_results = await search_tavily(query)
        await asyncio.sleep(0.5)

        # Step 2: Broadcasting Status 2
        status_msg = "📖 Extracting insights from retrieved search sources..."
        await manager.broadcast_to_room(room_id, {
            "type": "research_status",
            "content": status_msg
        })
        yield f"data: {json.dumps({'type': 'status', 'content': status_msg})}\n\n"
        await asyncio.sleep(0.5)

        # Step 3: Broadcasting Status 3
        status_msg = "✍️ Synthesizing findings and drafting report..."
        await manager.broadcast_to_room(room_id, {
            "type": "research_status",
            "content": status_msg
        })
        yield f"data: {json.dumps({'type': 'status', 'content': status_msg})}\n\n"
        await asyncio.sleep(0.5)

        # Format retrieved search snippets
        results_list = tavily_results.get("results", [])
        search_snippets = []
        for r in results_list:
            search_snippets.append(
                f"SOURCE: {r.get('url')}\n"
                f"TITLE: {r.get('title')}\n"
                f"CONTENT: {r.get('content')}"
            )
        search_context = "\n\n".join(search_snippets) if search_snippets else "No web results found."

        # Step 4: Assemble query messages for LLM incorporating real-time Tavily search context
        system_prompt = "You are a professional research agent specializing in contract analysis, corporate policies, and legal/regulatory compliance."
        user_prompt = f"""Please perform deep research and compile a highly structured report on the following query:

QUERY: "{query}"

LIVE WEB SEARCH RESULTS (TAVILY):
{search_context}

If relevant, consider this contract/document context:
CONTRACT/DOCUMENT CONTEXT:
{contract}

Output your findings in clean markdown, covering key definitions, legal requirements, potential risks, and recommendations."""

        query_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Broadcast stream_start
        stream_id = str(ObjectId())
        await manager.broadcast_to_room(room_id, {
            "type": "stream_start",
            "id": stream_id,
            "sender_name": "ResearchBot"
        })
        
        full_response = ""
        token_count = 0
        
        # Stream from NVIDIA API Client
        async for chunk in nvidia_client.generate_stream(query_messages, temperature=0.5):
            full_response += chunk
            token_count += 1
            
            # Broadcast token
            await manager.broadcast_to_room(room_id, {
                "type": "stream_token",
                "id": stream_id,
                "content": chunk,
                "token_count": token_count
            })
            yield f"data: {json.dumps({'type': 'token', 'content': chunk, 'token_count': token_count})}\n\n"
            
        # Send stream_end
        await manager.broadcast_to_room(room_id, {
            "type": "stream_end",
            "id": stream_id
        })
        
        # Save Research message in DB
        research_msg = {
            "room_id": room_id,
            "user_id": "system",
            "username": "ResearchBot",
            "content": f"### Research Report: {query}\n\n" + full_response,
            "message_type": "agent",
            "created_at": datetime.utcnow()
        }
        msg_result = await db["messages"].insert_one(research_msg)
        
        # Save Canvas Output card
        agent_output = {
            "room_id": room_id,
            "message_id": str(msg_result.inserted_id),
            "title": f"Research: {query[:30]}",
            "content": f"### Research Report: {query}\n\n" + full_response,
            "status": "draft",
            "edited_by": None,
            "edited_at": None,
            "created_at": datetime.utcnow()
        }
        await db["agent_outputs"].insert_one(agent_output)
        
        # Broadcast final message
        await manager.broadcast_to_room(room_id, {
            "type": "message",
            "id": str(msg_result.inserted_id),
            "room_id": room_id,
            "user_id": "system",
            "username": "ResearchBot",
            "content": f"### Research Report: {query}\n\n" + full_response,
            "message_type": "agent",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(research_event_generator(), media_type="text/event-stream")
