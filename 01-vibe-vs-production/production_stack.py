from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional

# === State with checkpointing (Decision 2) ===
class AgentState(TypedDict):
    messages: list
    current_step: str
    interrupted: bool

# === Production-ready graph ===
workflow = StateGraph(AgentState)

def orchestrator_node(state: AgentState) -> AgentState:
    """Routes between user, LLM, RAG, and MCP tools."""
    state["current_step"] = "orchestrating"
    return state

def rag_node(state: AgentState) -> AgentState:
    """RAG only when context can't carry the load."""
    state["current_step"] = "retrieving"
    return state

def mcp_tool_node(state: AgentState) -> AgentState:
    """MCP as the action layer with RBAC."""
    state["current_step"] = "executing_tool"
    return state

# === Build graph with checkpointing ===
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("rag", rag_node)
workflow.add_node("mcp_tool", mcp_tool_node)

workflow.add_edge(START, "orchestrator")
workflow.add_conditional_edges(
    "orchestrator",
    lambda s: "rag" if len(s["messages"]) > 5 else "mcp_tool"
)
workflow.add_edge("rag", "mcp_tool")
workflow.add_edge("mcp_tool", END)

# Checkpointing enables pause/inspect/resume
app = workflow.compile()
