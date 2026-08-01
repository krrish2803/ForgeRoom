import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.auth.security import get_current_user
from app.models.user import UserInDB
from app.orgs.routes import get_org_member_role, log_org_action
import uuid

logger = logging.getLogger("uvicorn")
router = APIRouter()

# 1. GET Pre-built library agents
@router.get("/library", response_model=List[Dict[str, Any]])
async def get_library_agents(current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    cursor = db["agents_library"].find()
    agents = await cursor.to_list(length=100)
    for a in agents:
        a["slug"] = a["_id"]
    return agents

# 2. GET custom org agents + library overrides
@router.get("/orgs/{org_id}/agents")
async def get_org_agents(org_id: str, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    # Verify membership
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if not role:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
        
    # Get seeded library agents
    lib_cursor = db["agents_library"].find()
    lib_agents = await lib_cursor.to_list(length=100)
    lib_map = {a["_id"]: a for a in lib_agents}
    
    # Get org custom settings / overrides
    org_cursor = db["org_agents"].find({"org_id": org_id})
    org_agents = await org_cursor.to_list(length=100)
    
    # Merge library agents with org overrides, and include completely custom agents
    merged = []
    overridden_slugs = set()
    
    for oa in org_agents:
        oa["id"] = str(oa["_id"])
        # Check if this overrides a library slug
        slug = oa.get("agent_id")
        if slug in lib_map:
            # Overriding a pre-built agent
            merged.append({
                "slug": slug,
                "name": oa["name"],
                "description": oa["description"],
                "icon": oa["icon"],
                "system_prompt": oa["system_prompt"],
                "suggested_model": oa["model_name"],
                "temperature": oa["temperature"],
                "version": oa["version"],
                "is_custom": False,
                "is_overridden": True
            })
            overridden_slugs.add(slug)
        else:
            # Completely custom org-specific agent
            merged.append({
                "slug": oa["agent_id"],
                "name": oa["name"],
                "description": oa["description"],
                "icon": oa["icon"],
                "system_prompt": oa["system_prompt"],
                "suggested_model": oa["model_name"],
                "temperature": oa["temperature"],
                "version": oa["version"],
                "is_custom": True,
                "is_overridden": False
            })
            
    # Include non-overridden library agents
    for slug, la in lib_map.items():
        if slug not in overridden_slugs:
            merged.append({
                "slug": slug,
                "name": la["name"],
                "description": la["description"],
                "icon": la["icon"],
                "system_prompt": la["system_prompt"],
                "suggested_model": la["suggested_model"],
                "temperature": la["temperature"],
                "version": 1,
                "is_custom": False,
                "is_overridden": False
            })
            
    return merged

# 3. POST Create custom agent (or create library override)
@router.post("/orgs/{org_id}/agents")
async def create_org_agent(org_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role not in ["owner", "editor"]:
        raise HTTPException(status_code=403, detail="Viewer role cannot create custom agents")
        
    name = data.get("name")
    description = data.get("description", "")
    icon = data.get("icon", "🤖")
    system_prompt = data.get("system_prompt")
    model_name = data.get("model_name", "meta/llama-3.1-70b-instruct")
    temperature = float(data.get("temperature", 0.5))
    agent_id = data.get("agent_id")  # Could be slug of library agent if overriding, otherwise generated
    
    if not name or not system_prompt:
        raise HTTPException(status_code=400, detail="name and system_prompt are required")
        
    if not agent_id:
        agent_id = f"custom-{uuid.uuid4().hex[:8]}"
        
    # Check if duplicate in org
    existing = await db["org_agents"].find_one({"org_id": org_id, "agent_id": agent_id})
    if existing:
        raise HTTPException(status_code=400, detail=f"Agent '{agent_id}' already configured for this organization")
        
    doc = {
        "org_id": org_id,
        "agent_id": agent_id,
        "name": name,
        "description": description,
        "icon": icon,
        "system_prompt": system_prompt,
        "model_name": model_name,
        "temperature": temperature,
        "version": 1,
        "created_by": str(current_user.id),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    res = await db["org_agents"].insert_one(doc)
    doc["id"] = str(res.inserted_id)
    if "_id" in doc:
        del doc["_id"]
    
    # Save first version in history
    await db["org_agent_versions"].insert_one({
        "org_id": org_id,
        "agent_id": agent_id,
        "version": 1,
        "system_prompt": system_prompt,
        "model_name": model_name,
        "temperature": temperature,
        "updated_by": str(current_user.id),
        "updated_at": datetime.utcnow()
    })
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "agent_created", f"Created or customized agent '{name}' ({agent_id})."
    )
    
    return doc

# 4. PATCH Update custom agent (saves prompt version history)
@router.patch("/orgs/{org_id}/agents/{agent_id}")
async def update_org_agent(org_id: str, agent_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role not in ["owner", "editor"]:
        raise HTTPException(status_code=403, detail="Viewer role cannot update agents")
        
    # Check if this configuration already exists in org_agents
    existing = await db["org_agents"].find_one({"org_id": org_id, "agent_id": agent_id})
    
    name = data.get("name")
    description = data.get("description")
    icon = data.get("icon")
    system_prompt = data.get("system_prompt")
    model_name = data.get("model_name")
    temperature = data.get("temperature")
    
    if not existing:
        # If it doesn't exist, check if agent_id is a library slug to automatically instantiate override config
        lib_agent = await db["agents_library"].find_one({"_id": agent_id})
        if not lib_agent:
            raise HTTPException(status_code=404, detail="Agent configuration not found")
            
        # Create initial override config (representing original library state before edits)
        existing = {
            "org_id": org_id,
            "agent_id": agent_id,
            "name": lib_agent["name"],
            "description": lib_agent["description"],
            "icon": lib_agent["icon"],
            "system_prompt": lib_agent["system_prompt"],
            "model_name": lib_agent["suggested_model"],
            "temperature": lib_agent["temperature"],
            "version": 1,
            "created_by": str(current_user.id),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        res = await db["org_agents"].insert_one(existing)
        existing["_id"] = res.inserted_id
        
        # Save version 1 (original version)
        await db["org_agent_versions"].insert_one({
            "org_id": org_id,
            "agent_id": agent_id,
            "version": 1,
            "system_prompt": existing["system_prompt"],
            "model_name": existing["model_name"],
            "temperature": existing["temperature"],
            "updated_by": str(current_user.id),
            "updated_at": datetime.utcnow()
        })
        
    # Increment version
    next_version = existing.get("version", 1) + 1
    
    update_doc = {"updated_at": datetime.utcnow(), "version": next_version}
    if name: update_doc["name"] = name
    if description is not None: update_doc["description"] = description
    if icon: update_doc["icon"] = icon
    if system_prompt: update_doc["system_prompt"] = system_prompt
    if model_name: update_doc["model_name"] = model_name
    if temperature is not None: update_doc["temperature"] = float(temperature)
    
    await db["org_agents"].update_one({"_id": existing["_id"]}, {"$set": update_doc})
    
    # Save historical snapshot version
    await db["org_agent_versions"].insert_one({
        "org_id": org_id,
        "agent_id": agent_id,
        "version": next_version,
        "system_prompt": system_prompt or existing["system_prompt"],
        "model_name": model_name or existing["model_name"],
        "temperature": float(temperature) if temperature is not None else existing["temperature"],
        "updated_by": str(current_user.id),
        "updated_at": datetime.utcnow()
    })
    
    # Audit log
    agent_name = name or existing["name"]
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "agent_updated", f"Updated agent prompt '{agent_name}' ({agent_id}) to v{next_version}."
    )
    
    updated = await db["org_agents"].find_one({"_id": existing["_id"]})
    updated["id"] = str(updated["_id"])
    if "_id" in updated:
        del updated["_id"]
    return updated

# 5. GET Agent Prompt Version History List
@router.get("/orgs/{org_id}/agents/{agent_id}/versions")
async def get_agent_versions(org_id: str, agent_id: str, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if not role:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
        
    cursor = db["org_agent_versions"].find({"org_id": org_id, "agent_id": agent_id}).sort("version", -1)
    versions = await cursor.to_list(length=100)
    for v in versions:
        v["id"] = str(v["_id"])
        if "_id" in v:
            del v["_id"]
    return versions

# 6. POST Revert Agent prompt to specific version
@router.post("/orgs/{org_id}/agents/{agent_id}/revert")
async def revert_agent_version(org_id: str, agent_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role not in ["owner", "editor"]:
        raise HTTPException(status_code=403, detail="Viewer role cannot revert prompts")
        
    target_version = int(data.get("version"))
    if not target_version:
        raise HTTPException(status_code=400, detail="version is required")
        
    # Find targeted version record
    v_rec = await db["org_agent_versions"].find_one({
        "org_id": org_id,
        "agent_id": agent_id,
        "version": target_version
    })
    if not v_rec:
        raise HTTPException(status_code=404, detail=f"Version {target_version} history record not found")
        
    # Check if custom agent exists in org_agents
    existing = await db["org_agents"].find_one({"org_id": org_id, "agent_id": agent_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Active agent configuration not found")
        
    # Increment version count for the rollback event
    rollback_version = existing["version"] + 1
    
    update_doc = {
        "system_prompt": v_rec["system_prompt"],
        "model_name": v_rec["model_name"],
        "temperature": v_rec["temperature"],
        "version": rollback_version,
        "updated_at": datetime.utcnow()
    }
    
    await db["org_agents"].update_one({"_id": existing["_id"]}, {"$set": update_doc})
    
    # Save the new version
    await db["org_agent_versions"].insert_one({
        "org_id": org_id,
        "agent_id": agent_id,
        "version": rollback_version,
        "system_prompt": v_rec["system_prompt"],
        "model_name": v_rec["model_name"],
        "temperature": v_rec["temperature"],
        "updated_by": str(current_user.id),
        "updated_at": datetime.utcnow()
    })
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "agent_reverted", f"Reverted agent prompt '{existing['name']}' ({agent_id}) to version {target_version} (new state saved as v{rollback_version})."
    )
    
    updated = await db["org_agents"].find_one({"_id": existing["_id"]})
    updated["id"] = str(updated["_id"])
    if "_id" in updated:
        del updated["_id"]
    return updated

# 7. GET Multi-agent pipeline chains list
@router.get("/orgs/{org_id}/chains")
async def list_org_chains(org_id: str, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if not role:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
        
    cursor = db["org_agent_chains"].find({"org_id": org_id})
    chains = await cursor.to_list(length=100)
    for c in chains:
        c["id"] = str(c["_id"])
        if "_id" in c:
            del c["_id"]
    return chains

# 8. POST Create multi-agent chain
@router.post("/orgs/{org_id}/chains")
async def create_org_chain(org_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role not in ["owner", "editor"]:
        raise HTTPException(status_code=403, detail="Viewer role cannot create chains")
        
    name = data.get("name")
    description = data.get("description", "")
    agents = data.get("agents") # Array of agent slugs/custom IDs
    
    if not name or not agents or len(agents) < 2:
        raise HTTPException(status_code=400, detail="name and a list of at least 2 agents are required")
        
    chain_id = str(uuid.uuid4())
    doc = {
        "_id": chain_id,
        "org_id": org_id,
        "name": name,
        "description": description,
        "agents": agents,
        "created_by": str(current_user.id),
        "created_at": datetime.utcnow()
    }
    
    await db["org_agent_chains"].insert_one(doc)
    doc["id"] = chain_id
    if "_id" in doc:
        del doc["_id"]
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "chain_created", f"Created agent chain workflow '{name}' with sequence: {agents}."
    )
    
    return doc

# 9. DELETE Multi-agent chain
@router.delete("/orgs/{org_id}/chains/{chain_id}")
async def delete_org_chain(org_id: str, chain_id: str, current_user: UserInDB = Depends(get_current_user)):
    db = get_db()
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role not in ["owner", "editor"]:
        raise HTTPException(status_code=403, detail="Viewer role cannot delete chains")
        
    res = await db["org_agent_chains"].delete_one({"_id": chain_id, "org_id": org_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chain not found")
        
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "chain_deleted", f"Deleted agent chain workflow ID: {chain_id}."
    )
    
    return {"status": "success", "detail": "Chain workflow deleted"}
