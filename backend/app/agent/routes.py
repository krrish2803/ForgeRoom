import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from app.database import get_db
from app.auth.security import get_current_user
from app.models.user import UserInDB
from app.agent.nvidia import nvidia_client
from app.agent.graph import get_agent_graph
from app.websocket.manager import manager
from app.agent.streams import get_stream_context, remove_stream_context
from bson import ObjectId

router = APIRouter(tags=["agent"])
logger = logging.getLogger("uvicorn")

async def get_agent_settings(db, org_id: Optional[str], agent_id: str) -> dict:
    # 1. Check org custom overrides / custom agents
    if org_id:
        custom_agent = await db["org_agents"].find_one({"org_id": org_id, "agent_id": agent_id})
        if custom_agent:
            return {
                "name": custom_agent.get("name"),
                "system_prompt": custom_agent.get("system_prompt"),
                "model_name": custom_agent.get("model_name"),
                "temperature": custom_agent.get("temperature", 0.5)
            }
            
    # 2. Check pre-built library agents
    lib_agent = await db["agents_library"].find_one({"_id": agent_id})
    if lib_agent:
        return {
            "name": lib_agent.get("name"),
            "system_prompt": lib_agent.get("system_prompt"),
            "model_name": lib_agent.get("suggested_model"),
            "temperature": lib_agent.get("temperature", 0.5)
        }
        
    # Default fallback
    return {
        "name": "ForgeBot",
        "system_prompt": "You are a professional AI assistant.",
        "model_name": None,
        "temperature": 0.5
    }

@router.post("/agent/respond")
@router.post("/agent/stream")
async def agent_respond(data: dict, current_user: Optional[UserInDB] = Depends(get_current_user)):
    """
    Triggers the LangGraph agent review and streams responses back.
    Includes support for pause, resume, and redirect signals.
    data = {
        "room_id": str,
        "user_message": str,
        "conversation_history": list
    }
    """
    room_id = data["room_id"]
    user_message = data["user_message"]
    
    db = get_db()
    
    # 1. Fetch Room Context
    room_doc = await db["rooms"].find_one({"_id": room_id})
    if not room_doc:
        raise HTTPException(status_code=404, detail="Room not found")
        
    # Check Org scope and RBAC permissions if Org room
    org_id = room_doc.get("org_id")
    if org_id and current_user:
        member = await db["org_members"].find_one({"org_id": org_id, "user_id": str(current_user.id)})
        if not member or member["role"] == "viewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewer role cannot trigger agent responds"
            )
            
    contract = room_doc.get("contract_text", "No contract loaded yet.")
    
    # Get active templates context if used
    starter_prompt = room_doc.get("metadata", {}).get("starter_prompt", "")
    
    messages_cursor = db["messages"].find({"room_id": room_id}).sort("created_at", 1)
    messages_list = await messages_cursor.to_list(length=15)
    
    decisions_cursor = db["agent_outputs"].find({"room_id": room_id, "status": "finalized"})
    decisions = await decisions_cursor.to_list(length=50)

    # 2. Build system instructions
    history_text = "\n".join([
        f"- {m['username']}: {m['content']}" if m['message_type'] == 'user' else f"- Agent: {m['content']}"
        for m in messages_list
    ])
    
    decisions_text = "\n".join([
        f"- {d['title']}: {d['content']}"
        for d in decisions
    ])
    
    # Load custom org agent configs if org room
    custom_instruction = "You are a contract review specialist working with a legal team."
    org_model = None
    org_temp = 0.5
    if org_id:
        org_config = await db["org_agent_configs"].find_one({"_id": org_id})
        if org_config:
            custom_instruction = org_config.get("system_prompt", custom_instruction)
            org_model = org_config.get("model_name")
            org_temp = org_config.get("temperature", org_temp)

    system_prompt = f"""{custom_instruction} You have been analyzing the following contract:

CONTRACT TEXT:
{contract}

CONVERSATION HISTORY (TEAM DISCUSSION):
{history_text}

PREVIOUS DECISIONS MADE:
{decisions_text}

TEMPLATE STARTER CONTEXT:
{starter_prompt}

INSTRUCTIONS:
1. Analyze the contract based on the user's question.
2. Reference previous decisions and discussions to maintain consistency.
3. Be concise but thorough.
4. If asked to correct or redirect your analysis, adjust.
5. Provide actionable insights.

REMEMBER: Multiple people are viewing your analysis in real time. Be collaborative, not authoritative."""

    # 3. Resolve active workflow (Agent Library / overrides / Chains)
    active_agent_id = room_doc.get("active_agent_id")
    active_chain_id = room_doc.get("active_chain_id")
    
    agent_ids = []
    if active_chain_id:
        chain_doc = await db["org_agent_chains"].find_one({"_id": active_chain_id})
        if chain_doc:
            agent_ids = chain_doc.get("agents", [])
            
    if not agent_ids and active_agent_id:
        agent_ids = [active_agent_id]
        
    if not agent_ids:
        agent_ids = ["default"]
        
    agent_instances = []
    for aid in agent_ids:
        if aid == "default":
            agent_instances.append({
                "id": "default",
                "name": "ForgeBot",
                "system_prompt": system_prompt,
                "model_name": org_model,
                "temperature": org_temp
            })
        else:
            settings = await get_agent_settings(db, org_id, aid)
            compiled_prompt = f"""{settings['system_prompt']}
            
CONTRACT TEXT:
{contract}

CONVERSATION HISTORY (TEAM DISCUSSION):
{history_text}

PREVIOUS DECISIONS MADE:
{decisions_text}

TEMPLATE STARTER CONTEXT:
{starter_prompt}

INSTRUCTIONS:
1. Perform your analysis based on your persona guidelines and the user's request.
2. Be concise but thorough.
"""
            agent_instances.append({
                "id": aid,
                "name": settings["name"],
                "system_prompt": compiled_prompt,
                "model_name": settings["model_name"],
                "temperature": settings["temperature"]
            })

    # Set up Stream context
    context = get_stream_context(room_id)
    context.resume() # Ensure start fresh (not paused)

    async def run_chain_step(step_idx: int, current_query: str, start_token_count: int = 0):
        if step_idx >= len(agent_instances):
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
            
        agent = agent_instances[step_idx]
        step_num = step_idx + 1
        total_steps = len(agent_instances)
        
        # Broadcast stream_start with step info
        sender_name = agent["name"]
        if total_steps > 1:
            sender_name += f" (Step {step_num}/{total_steps})"
            
        stream_id = str(ObjectId())
        await manager.broadcast_to_room(room_id, {
            "type": "stream_start",
            "id": stream_id,
            "sender_name": sender_name
        })
        
        query_messages = [
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": current_query}
        ]
        
        full_response = ""
        token_count = start_token_count
        
        # Stream from NVIDIA API
        async for chunk in nvidia_client.generate_stream(
            query_messages,
            temperature=agent["temperature"],
            model=agent["model_name"]
        ):
            # Check for cancellation
            if context.cancel_event.is_set():
                context.cancel_event.clear()
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
                
            # Check for pause
            if context.is_paused:
                await manager.broadcast_to_room(room_id, {"type": "paused"})
                yield f"data: {json.dumps({'type': 'paused', 'token_count': token_count})}\n\n"
                await context.pause_event.wait()
                
            # Check for redirect
            if context.redirect_message:
                redirect_text = context.redirect_message
                context.redirect_message = ""
                
                await manager.broadcast_to_room(room_id, {
                    "type": "redirected",
                    "new_message": redirect_text
                })
                yield f"data: {json.dumps({'type': 'redirected', 'new_message': redirect_text})}\n\n"
                
                async for sub_chunk in run_chain_step(step_idx, redirect_text, token_count):
                    yield sub_chunk
                return
                
            full_response += chunk
            token_count += 1
            
            await manager.broadcast_to_room(room_id, {
                "type": "stream_token",
                "id": stream_id,
                "content": chunk,
                "token_count": token_count
            })
            
            yield f"data: {json.dumps({'type': 'token', 'content': chunk, 'token_count': token_count})}\n\n"
            
        # Send stream_end for this step
        await manager.broadcast_to_room(room_id, {
            "type": "stream_end",
            "id": stream_id
        })
        
        # If there are more steps, proceed to next step
        if step_idx < total_steps - 1:
            next_query = f"""Here is the preceding step's output analysis for your review:

{full_response}

Based on this analysis and the original user query '{user_message}', please proceed with your instructions."""
            async for sub_chunk in run_chain_step(step_idx + 1, next_query):
                yield sub_chunk
        else:
            # Last step: save final result as message and card
            agent_msg = {
                "room_id": room_id,
                "user_id": "system",
                "username": "ForgeBot",
                "content": full_response,
                "message_type": "agent",
                "created_at": datetime.utcnow()
            }
            msg_result = await db["messages"].insert_one(agent_msg)
            
            # Save Canvas Output card
            agent_output = {
                "room_id": room_id,
                "message_id": str(msg_result.inserted_id),
                "title": f"Review Card - {datetime.utcnow().strftime('%H:%M:%S')}",
                "content": full_response,
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
                "username": "ForgeBot",
                "content": full_response,
                "message_type": "agent",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Sync persistent checkpointer state in LangGraph
            try:
                graph = get_agent_graph(db)
                config = {"configurable": {"thread_id": room_id}}
                await graph.ainvoke({
                    "messages": [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": full_response}
                    ],
                    "research_notes": [contract],
                    "current_topic": user_message,
                    "summary": full_response,
                    "next_action": "end"
                }, config=config)
            except Exception as e:
                logger.error(f"Failed to checkpoint graph: {e}")
                
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    async def event_generator():
        try:
            async for chunk in run_chain_step(0, user_message):
                yield chunk
        finally:
            remove_stream_context(room_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ==========================================
# STREAM CONTROL ENDPOINTS
# ==========================================
@router.post("/agent/{room_id}/pause")
async def pause_agent(room_id: str):
    """Pause the agent mid-generation"""
    context = get_stream_context(room_id)
    context.pause()
    # Broadcast to room
    await manager.broadcast_to_room(room_id, {"type": "paused"})
    return {"status": "paused"}

@router.post("/agent/{room_id}/resume")
async def resume_agent(room_id: str):
    """Resume the paused agent"""
    context = get_stream_context(room_id)
    context.resume()
    # Broadcast to room
    await manager.broadcast_to_room(room_id, {"type": "resumed"})
    return {"status": "resumed"}

@router.post("/agent/{room_id}/redirect")
async def redirect_agent(room_id: str, data: dict):
    """Redirect agent generation with new instructions"""
    msg = data.get("message", "")
    if not msg:
         raise HTTPException(status_code=400, detail="message instruction required")
    context = get_stream_context(room_id)
    context.redirect(msg)
    return {"status": "redirected"}

@router.post("/agent/{room_id}/takeover")
async def takeover_agent(room_id: str):
    """Stop agent stream to let human take over typing"""
    context = get_stream_context(room_id)
    context.cancel()
    await manager.broadcast_to_room(room_id, {"type": "stream_end"})
    return {"status": "takeover_complete"}

# ==========================================
# FEATURE 10: SUMMARIZE ENDPOINT
# ==========================================
@router.post("/rooms/{room_id}/summarize")
async def summarize_room(room_id: str):
    """Summarize room contract review, extracting decisions and actions"""
    db = get_db()
    
    # 1. Fetch Room Messages
    messages_cursor = db["messages"].find({"room_id": room_id}).sort("created_at", 1)
    messages = await messages_cursor.to_list(length=100)
    
    if not messages:
        return {
            "summary": {
                "summary": "No messages in this workspace yet.",
                "decisions": [],
                "action_items": [],
                "open_questions": []
            },
            "markdown": "# Meeting Summary\n\nNo transcript available yet."
        }
        
    transcript = "\n".join([
        f"{msg['username']}: {msg['content']}"
        for msg in messages
    ])
    
    # Prompt NVIDIA API for JSON summary schema
    summary_prompt = f"""You are facilitating a legal contract review session summary. Extract the following information from the meeting transcript:
1. A concise overview summary paragraph.
2. Key decisions made.
3. Action items (who is responsible, the task, and a deadline if discussed).
4. Open questions.

TRANSCRIPT:
{transcript}

You MUST respond ONLY with a valid JSON document conforming to this exact structure:
{{
    "summary": "A brief overview summary text here.",
    "decisions": [
        {{"decision": "Specific decision", "owner": "Name", "timestamp": "hh:mm"}}
    ],
    "action_items": [
        {{"item": "Task statement", "owner": "Name", "deadline": "date or N/A"}}
    ],
    "open_questions": ["Question 1", "Question 2"]
}}"""

    response_text = await nvidia_client.generate([
        {"role": "system", "content": "You are a professional compiler. Return JSON only."},
        {"role": "user", "content": summary_prompt}
    ])
    
    # Sanitize markdown ticks block if generated by LLM
    clean_json = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        result = json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to parse summary output JSON: {e}. Output was: {response_text}")
        result = {
            "summary": "Summary compiled successfully, but formatting was incorrect.",
            "decisions": [],
            "action_items": [],
            "open_questions": []
        }
        
    # Build Markdown string
    md = f"""# Workspace Session Summary

## Overview
{result.get('summary', 'No summary available.')}

## Decisions Matrix
"""
    if result.get("decisions"):
        for d in result["decisions"]:
            md += f"- **{d['decision']}** (Owner: {d.get('owner', 'N/A')})\n"
    else:
         md += "_No key decisions recorded yet._\n"
         
    md += "\n## Action Items Checklist\n"
    if result.get("action_items"):
        for a in result["action_items"]:
            md += f"- [ ] {a['item']} — **{a.get('owner', 'N/A')}** (Deadline: {a.get('deadline', 'N/A')})\n"
    else:
         md += "_No action items assigned._\n"
         
    md += "\n## Open Questions\n"
    if result.get("open_questions"):
        for q in result["open_questions"]:
            md += f"- {q}\n"
    else:
         md += "_No pending questions recorded._\n"
         
    return {
        "summary": result,
        "markdown": md
    }
