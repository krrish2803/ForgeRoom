import operator
from typing import Annotated, Dict, List, TypedDict, Literal, Any
from langgraph.graph import StateGraph, END
from app.agent.nvidia import nvidia_client
from app.agent.checkpoint import MongoDBSaver
from motor.motor_asyncio import AsyncIOMotorDatabase

# 1. State Definition
class AgentState(TypedDict):
    # Conversations history representing room message logs
    messages: Annotated[List[Dict[str, str]], operator.add]
    # Research notes extracted during agent operations
    research_notes: Annotated[List[str], operator.add]
    # Current topic/prompt under investigation
    current_topic: str
    # The final synthesized collaborative result
    summary: str
    # Control signal: "research" | "summarize" | "end"
    next_action: str

# ==========================================
# 2. NODE DEFINITIONS
# ==========================================
async def research_node(state: AgentState) -> Dict[str, Any]:
    """Node that uses NVIDIA LLM to perform deep domain lookup."""
    topic = state.get("current_topic", "General Collaboration")
    messages = state.get("messages", [])
    
    prompt = (
        f"You are the Research Agent for the ForgeRoom platform. Your task is to investigate "
        f"the topic: '{topic}' and extract 3 key facts, definitions, or insights. "
        f"Structure your findings in bullet points.\n\n"
        f"Prior conversation context: {messages[-3:] if len(messages) > 3 else messages}"
    )
    
    # Request completion from NVIDIA API
    response = await nvidia_client.generate([
        {"role": "system", "content": "You are a professional enterprise researcher."},
        {"role": "user", "content": prompt}
    ])
    
    return {
        "research_notes": [response],
        "next_action": "summarize"
    }

async def summarize_node(state: AgentState) -> Dict[str, Any]:
    """Node that synthesizes research notes into a premium summary output."""
    notes = state.get("research_notes", [])
    topic = state.get("current_topic", "General Collaboration")
    
    prompt = (
        f"You are the Synthesizer Agent. Take the following raw research notes: {notes}\n\n"
        f"Create a clean, executive-level markdown summary of these findings "
        f"focused on topic: '{topic}'. Do not include conversational filler, "
        f"output the raw markdown document."
    )
    
    response = await nvidia_client.generate([
        {"role": "system", "content": "You are a senior technical writer compiling final summaries."},
        {"role": "user", "content": prompt}
    ])
    
    return {
        "summary": response,
        "messages": [{"role": "assistant", "content": response}],
        "next_action": "end"
    }

# ==========================================
# 3. ROUTER / CONDITIONAL EDGES
# ==========================================
def route_next_action(state: AgentState) -> Literal["research", "summarize", "__end__"]:
    action = state.get("next_action", "research")
    if action == "summarize":
        return "summarize"
    elif action == "end":
        return "__end__"
    return "research"

# ==========================================
# 4. GRAPH COMPILATION
# ==========================================
def get_agent_graph(db: AsyncIOMotorDatabase):
    # Initialize StateGraph builder
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("research", research_node)
    workflow.add_node("summarize", summarize_node)
    
    # Set Entry Point
    workflow.set_entry_point("research")
    
    # Add Conditional Edges
    workflow.add_conditional_edges(
        "research",
        route_next_action,
        {
            "research": "research",
            "summarize": "summarize",
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "summarize",
        route_next_action,
        {
            "research": "research",
            "summarize": "summarize",
            "__end__": END
        }
    )
    
    # Initialize Mongo persistent checkpointer
    checkpointer = MongoDBSaver(db)
    
    # Compile Graph
    return workflow.compile(checkpointer=checkpointer)
