import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger("uvicorn")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    logger.info(f"Connecting to MongoDB at {settings.mongodb_url}...")
    db_instance.client = AsyncIOMotorClient(settings.mongodb_url)
    db_instance.db = db_instance.client[settings.database_name]
    
    # Index Configurations
    users = db_instance.db["users"]
    await users.create_index("email", unique=True)
    
    rooms = db_instance.db["rooms"]
    await rooms.create_index("created_by")
    
    participants = db_instance.db["room_participants"]
    await participants.create_index([("room_id", 1), ("user_id", 1)], unique=True)
    await participants.create_index("last_seen")
    
    messages = db_instance.db["messages"]
    await messages.create_index([("room_id", 1), ("created_at", 1)])
    
    agent_outputs = db_instance.db["agent_outputs"]
    await agent_outputs.create_index("room_id")
    
    versions = db_instance.db["session_versions"]
    await versions.create_index([("room_id", 1), ("version_number", 1)], unique=True)
    
    v_messages = db_instance.db["version_messages"]
    await v_messages.create_index("version_id")
    
    # Org Workspace indexes
    organizations = db_instance.db["organizations"]
    await organizations.create_index("created_by")

    org_members = db_instance.db["org_members"]
    await org_members.create_index([("org_id", 1), ("user_id", 1)], unique=True)
    await org_members.create_index("user_id")

    org_audit_logs = db_instance.db["org_audit_logs"]
    await org_audit_logs.create_index([("org_id", 1), ("timestamp", -1)])

    # Agent Library and customization indexes
    org_agents = db_instance.db["org_agents"]
    await org_agents.create_index([("org_id", 1), ("agent_id", 1)], unique=True)

    org_agent_versions = db_instance.db["org_agent_versions"]
    await org_agent_versions.create_index([("org_id", 1), ("agent_id", 1), ("version", -1)])

    org_agent_chains = db_instance.db["org_agent_chains"]
    await org_agent_chains.create_index("org_id")
    
    # Seed default templates & agent library
    await seed_templates(db_instance.db)
    await seed_agents(db_instance.db)
    
    logger.info("Connected to MongoDB successfully and loaded all collection indexes.")

async def seed_templates(db):
    templates_col = db["templates"]
    
    default_templates = [
        {
            "_id": "product-brainstorm",
            "name": "Product Brainstorm",
            "slug": "product-brainstorm",
            "description": "Explore and refine product ideas with a team",
            "icon": "💡",
            "starter_prompt": "You are facilitating a product brainstorm session. Help the team explore market opportunities, user pain points, and innovative solutions.",
            "suggested_agents": ["researcher", "strategist"]
        },
        {
            "_id": "marketing-campaign",
            "name": "Marketing Campaign",
            "slug": "marketing-campaign",
            "description": "Develop marketing strategy and content ideas",
            "icon": "📢",
            "starter_prompt": "You are a marketing strategist. Help develop campaign themes, target audiences, messaging, and content ideas.",
            "suggested_agents": ["strategist", "writer", "critic"]
        },
        {
            "_id": "code-review",
            "name": "Code Review Session",
            "slug": "code-review",
            "description": "Review code with team and AI assistance",
            "icon": "💻",
            "starter_prompt": "You are an expert code reviewer. Analyze code for quality, security, performance, and suggest improvements.",
            "suggested_agents": ["coder", "critic"]
        },
        {
            "_id": "business-strategy",
            "name": "Business Strategy",
            "slug": "business-strategy",
            "description": "Develop strategic plans and roadmaps",
            "icon": "📊",
            "starter_prompt": "You are a business strategist. Help develop strategic initiatives, competitive analysis, and execution roadmaps.",
            "suggested_agents": ["strategist", "critic"]
        },
        {
            "_id": "contract-review",
            "name": "Contract Clause Review",
            "slug": "contract-review",
            "description": "Review contracts and analyze risk collaboratively",
            "icon": "📄",
            "starter_prompt": "You are a contract review specialist working with a legal team. Help analyze risk clauses and decisions.",
            "suggested_agents": ["lawyer", "critic"]
        }
    ]
    
    for t in default_templates:
        await templates_col.update_one(
            {"_id": t["_id"]},
            {"$set": t},
            upsert=True
        )

async def seed_agents(db):
    agents_col = db["agents_library"]
    
    default_agents = [
        {
            "_id": "legal-analyst",
            "name": "Legal Analyst",
            "description": "Analyze contract clauses, legal terms, and risk implications",
            "icon": "⚖️",
            "system_prompt": "You are a senior contract analyst. Your goal is to review contract clauses, pinpoint legal liabilities, highlight hidden risks, and suggest revisions to protect the organization's interests.",
            "suggested_model": "meta/llama-3.1-70b-instruct",
            "temperature": 0.3
        },
        {
            "_id": "sales-discovery",
            "name": "Sales Discovery",
            "description": "Analyze prospect notes, map customer needs, and formulate discovery questions",
            "icon": "🔍",
            "system_prompt": "You are a sales discovery consultant. Your goal is to identify customer pain points, budget triggers, purchase authority, and timeline constraints. Draft strategic discovery questions and map out next steps.",
            "suggested_model": "meta/llama-3.1-8b-instruct",
            "temperature": 0.5
        },
        {
            "_id": "support-triage",
            "name": "Support Triage",
            "description": "Classify incoming support tickets, assign severity, and generate troubleshooting guides",
            "icon": "🚨",
            "system_prompt": "You are a technical support coordinator. Analyze incoming support tickets, classify them into priority levels (P0-P3), assess business impact, and suggest immediate troubleshooting instructions.",
            "suggested_model": "meta/llama-3.1-8b-instruct",
            "temperature": 0.2
        },
        {
            "_id": "code-reviewer",
            "name": "Code Reviewer",
            "description": "Inspect code snippets for bugs, security concerns, performance issues, and styling guidelines",
            "icon": "💻",
            "system_prompt": "You are a senior staff software engineer performing a code review. Scan code submissions for bugs, security vulnerabilities, memory leaks, and performance optimization opportunities. Suggest modern, refactored code fixes.",
            "suggested_model": "meta/llama-3.1-70b-instruct",
            "temperature": 0.1
        },
        {
            "_id": "content-editor",
            "name": "Content Editor",
            "description": "Refine drafts for tone consistency, target audience appeal, grammatical clarity, and SEO impact",
            "icon": "✍️",
            "system_prompt": "You are an expert content editor. Review copy drafts to enhance punchiness, clear grammar, narrative flow, brand tone consistency, and search engine optimization (SEO) positioning.",
            "suggested_model": "meta/llama-3.1-8b-instruct",
            "temperature": 0.6
        },
        {
            "_id": "critic",
            "name": "Critic",
            "description": "Review drafts or solutions, detect loopholes, and provide suggestions for improvement",
            "icon": "🕵️",
            "system_prompt": "You are an expert Critic. Your job is to analyze the preceding draft or solution, find gaps, logical fallacies, edge cases, or potential concerns, and write constructive criticisms.",
            "suggested_model": "meta/llama-3.1-70b-instruct",
            "temperature": 0.4
        },
        {
            "_id": "summarizer",
            "name": "Summarizer",
            "description": "Synthesize analysis notes into a clean, executive markdown document",
            "icon": "📋",
            "system_prompt": "You are an expert Summarizer. Take the inputs, reviews, or raw analysis steps, and synthesize them into a clean, executive-level markdown summary, focusing on actionable decisions and takeaways.",
            "suggested_model": "meta/llama-3.1-8b-instruct",
            "temperature": 0.3
        }
    ]
    
    for a in default_agents:
        await agents_col.update_one(
            {"_id": a["_id"]},
            {"$set": a},
            upsert=True
        )

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logger.info("MongoDB connection closed.")

def get_db():
    return db_instance.db
