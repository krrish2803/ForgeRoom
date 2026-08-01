import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.auth.security import get_current_user
from app.models.user import UserInDB
from app.models.org import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationInDB,
    OrgMemberResponse,
    OrgMemberInDB,
    OrgAgentConfigResponse,
    OrgAgentConfigBase,
    OrgAgentConfigInDB,
    OrgAuditLogResponse,
    OrgAuditLogInDB
)
from bson import ObjectId

router = APIRouter(prefix="/orgs", tags=["orgs"])

async def log_org_action(db, org_id: str, user_id: str, username: str, action: str, details: str, room_id: str = None):
    """Log an audit trail entry for compliance tracking"""
    log_db = OrgAuditLogInDB(
        org_id=org_id,
        room_id=room_id,
        user_id=user_id,
        username=username,
        action=action,
        details=details
    )
    await db["org_audit_logs"].insert_one(log_db.model_dump(by_alias=True, exclude=["id"]))

async def get_org_member_role(db, org_id: str, user_id: str) -> str:
    """Helper to retrieve user role in an org. Raises 403 if not a member."""
    member = await db["org_members"].find_one({"org_id": org_id, "user_id": user_id})
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    return member["role"]

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(data: OrganizationCreate, current_user: UserInDB = Depends(get_current_user)):
    """Create a new Organization workspace"""
    db = get_db()
    org_id = str(uuid.uuid4())
    
    org_db = OrganizationInDB(
        _id=org_id,
        name=data.name,
        created_by=str(current_user.id),
        created_at=datetime.utcnow()
    )
    
    await db["organizations"].insert_one(org_db.model_dump(by_alias=True))
    
    # Auto-add creator as Owner
    member_db = OrgMemberInDB(
        org_id=org_id,
        user_id=str(current_user.id),
        username=current_user.name,
        role="owner"
    )
    await db["org_members"].insert_one(member_db.model_dump(by_alias=True, exclude=["id"]))
    
    # Initialize default agent config for the org
    agent_config = OrgAgentConfigInDB(
        _id=org_id, # Maps to org_id
        system_prompt="You are a legal review specialist. Analyze the contract carefully.",
        temperature=0.5,
        model_name="meta/llama-3.1-70b-instruct"
    )
    await db["org_agent_configs"].insert_one(agent_config.model_dump(by_alias=True))
    
    # Audit trail
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "org_created", f"Organization '{data.name}' created by {current_user.name}."
    )
    
    org_doc = await db["organizations"].find_one({"_id": org_id})
    return OrganizationResponse(**org_doc)

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(current_user: UserInDB = Depends(get_current_user)):
    """List all organizations the current user belongs to"""
    db = get_db()
    # Find orgs where user is member
    cursor = db["org_members"].find({"user_id": str(current_user.id)})
    memberships = await cursor.to_list(length=100)
    
    org_ids = [m["org_id"] for m in memberships]
    if not org_ids:
        return []
        
    cursor_orgs = db["organizations"].find({"_id": {"$in": org_ids}})
    orgs = await cursor_orgs.to_list(length=100)
    return [OrganizationResponse(**o) for o in orgs]

@router.get("/{org_id}/members", response_model=List[OrgMemberResponse])
async def list_org_members(org_id: str, current_user: UserInDB = Depends(get_current_user)):
    """List all members of an organization"""
    db = get_db()
    # Verify current user membership
    await get_org_member_role(db, org_id, str(current_user.id))
    
    cursor = db["org_members"].find({"org_id": org_id})
    members = await cursor.to_list(length=100)
    
    # Convert _id fields
    out = []
    for m in members:
        m["id"] = str(m["_id"])
        out.append(OrgMemberResponse(**m))
    return out

@router.post("/{org_id}/members", response_model=OrgMemberResponse)
async def invite_member_to_org(org_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Invite/Add a user to the organization (Owner only)"""
    db = get_db()
    
    # 1. Verify role is Owner
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can invite members"
        )
        
    email = data.get("email")
    target_role = data.get("role", "viewer") # "owner" | "editor" | "viewer"
    
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
        
    # Check if target user exists
    user = await db["users"].find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not registered on ForgeRoom"
        )
        
    user_id = str(user["_id"])
    
    # Check if already a member
    existing = await db["org_members"].find_one({"org_id": org_id, "user_id": user_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )
        
    member_db = OrgMemberInDB(
        org_id=org_id,
        user_id=user_id,
        username=user["name"],
        role=target_role
    )
    
    result = await db["org_members"].insert_one(member_db.model_dump(by_alias=True, exclude=["id"]))
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "member_invited", f"Invited user '{user['name']}' ({email}) with role '{target_role}'."
    )
    
    member_doc = await db["org_members"].find_one({"_id": result.inserted_id})
    member_doc["id"] = str(member_doc["_id"])
    return OrgMemberResponse(**member_doc)

@router.patch("/{org_id}/members/{user_id}", response_model=OrgMemberResponse)
async def update_member_role(org_id: str, user_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Update organization member's role (Owner only)"""
    db = get_db()
    
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can modify member roles"
        )
        
    new_role = data.get("role")
    if new_role not in ["owner", "editor", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")
        
    # Find member doc
    member = await db["org_members"].find_one({"org_id": org_id, "user_id": user_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this organization")
        
    # Prevent editing own role to prevent lockout
    if user_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot modify your own role")
        
    await db["org_members"].update_one(
        {"org_id": org_id, "user_id": user_id},
        {"$set": {"role": new_role}}
    )
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "role_updated", f"Updated user '{member['username']}' role to '{new_role}'."
    )
    
    updated_doc = await db["org_members"].find_one({"org_id": org_id, "user_id": user_id})
    updated_doc["id"] = str(updated_doc["_id"])
    return OrgMemberResponse(**updated_doc)

@router.delete("/{org_id}/members/{user_id}")
async def remove_member_from_org(org_id: str, user_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Remove member from organization (Owner only)"""
    db = get_db()
    
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can remove members"
        )
        
    # Find member doc
    member = await db["org_members"].find_one({"org_id": org_id, "user_id": user_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this organization")
        
    if user_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the organization")
        
    await db["org_members"].delete_one({"org_id": org_id, "user_id": user_id})
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "member_removed", f"Removed user '{member['username']}' from organization."
    )
    
    return {"status": "member removed"}

@router.get("/{org_id}/audit-logs", response_model=List[OrgAuditLogResponse])
async def list_org_audit_logs(org_id: str, current_user: UserInDB = Depends(get_current_user)):
    """List organization audit logs for compliance tracking (Owner only)"""
    db = get_db()
    
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can view audit logs"
        )
        
    cursor = db["org_audit_logs"].find({"org_id": org_id}).sort("timestamp", -1)
    logs = await cursor.to_list(length=100)
    
    out = []
    for l in logs:
        l["id"] = str(l["_id"])
        out.append(OrgAuditLogResponse(**l))
    return out

@router.get("/{org_id}/agent-config", response_model=OrgAgentConfigResponse)
async def get_org_agent_config(org_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Get shared AI agent config for ForgeBot in the organization"""
    db = get_db()
    await get_org_member_role(db, org_id, str(current_user.id))
    
    config = await db["org_agent_configs"].find_one({"_id": org_id})
    if not config:
        # Fallback initialization
        config = {
            "_id": org_id,
            "system_prompt": "You are a legal review specialist. Analyze the contract carefully.",
            "temperature": 0.5,
            "model_name": "meta/llama-3.1-70b-instruct"
        }
        await db["org_agent_configs"].insert_one(config)
        
    config["org_id"] = config["_id"]
    return OrgAgentConfigResponse(**config)

@router.post("/{org_id}/agent-config", response_model=OrgAgentConfigResponse)
async def update_org_agent_config(org_id: str, data: OrgAgentConfigBase, current_user: UserInDB = Depends(get_current_user)):
    """Update shared AI agent config (Owner only)"""
    db = get_db()
    
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can update shared agent config"
        )
        
    await db["org_agent_configs"].update_one(
        {"_id": org_id},
        {"$set": data.model_dump()},
        upsert=True
    )
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "agent_config_updated", f"Updated shared agent configs (Temp: {data.temperature}, Model: {data.model_name})."
    )
    
    config = await db["org_agent_configs"].find_one({"_id": org_id})
    config["org_id"] = config["_id"]
    return OrgAgentConfigResponse(**config)

@router.get("/{org_id}/billing")
async def get_org_billing(org_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Get simple billing plan information for organization"""
    db = get_db()
    await get_org_member_role(db, org_id, str(current_user.id))
    
    org = await db["organizations"].find_one({"_id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    return {
        "org_id": org_id,
        "billing_plan": org.get("billing_plan", "Free"),
        "billing_status": org.get("billing_status", "active"),
        "created_at": org["created_at"].isoformat()
    }

@router.post("/{org_id}/billing")
async def update_org_billing(org_id: str, data: dict, current_user: UserInDB = Depends(get_current_user)):
    """Update organization billing plan subscription (Owner only)"""
    db = get_db()
    
    role = await get_org_member_role(db, org_id, str(current_user.id))
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can update billing plan"
        )
        
    new_plan = data.get("billing_plan")
    if new_plan not in ["Free", "Premium", "Enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid billing plan specified")
        
    await db["organizations"].update_one(
        {"_id": org_id},
        {"$set": {"billing_plan": new_plan}}
    )
    
    # Audit log
    await log_org_action(
        db, org_id, str(current_user.id), current_user.name,
        "billing_updated", f"Subscription billing plan updated to '{new_plan}'."
    )
    
    return {
        "status": "billing updated",
        "billing_plan": new_plan
    }
