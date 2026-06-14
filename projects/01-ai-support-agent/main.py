"""
End-to-end AI Support Agent combining all stack concepts:
LangGraph + RAG + MCP + Observability + Security
"""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint import MemorySaver
from dataclasses import dataclass
import operator

class AgentState(TypedDict):
    messages: Annotated[Sequence[dict], operator.add]
    user_id: str
    escalated: bool

checkpointer = MemorySaver()

@dataclass
class RAGEngine:
    def retrieve(self, query: str):
        return [f"Relevant doc about: {query}"]

@dataclass
class MCPSecurityGate:
    def check_permission(self, user_id: str, action: str) -> bool:
        return user_id.startswith("user_")

rag = RAGEngine()
security = MCPSecurityGate()

def classify(state: AgentState) -> AgentState:
    last = state["messages"][-1]["content"]
    if "password" in last.lower() or "refund" in last.lower():
        state["escalated"] = True
    return state

def handle_general(state: AgentState) -> AgentState:
    query = state["messages"][-1]["content"]
    docs = rag.retrieve(query)
    state["messages"].append({"role": "assistant",
                              "content": f"Answer: {docs[0]}"})
    return state

def handle_escalation(state: AgentState) -> AgentState:
    if not security.check_permission(state["user_id"], "escalate"):
        state["messages"].append({"role": "assistant",
                                  "content": "Access denied. Escalation requires admin."})
        return state
    state["messages"].append({"role": "assistant",
                              "content": "Escalated to human support (ticket #1234)"})
    return state

builder = StateGraph(AgentState)
builder.add_node("classify", classify)
builder.add_node("handle_general", handle_general)
builder.add_node("handle_escalation", handle_escalation)

builder.add_edge(START, "classify")
builder.add_conditional_edges(
    "classify",
    lambda s: "escalation" if s.get("escalated") else "general",
    {"general": "handle_general", "escalation": "handle_escalation"}
)
builder.add_edge("handle_general", END)
builder.add_edge("handle_escalation", END)

app = builder.compile(checkpointer=checkpointer)

result = app.invoke(
    {"messages": [{"role": "user", "content": "I forgot my password"}],
     "user_id": "user_42", "escalated": False},
    {"configurable": {"thread_id": "session_1"}}
)
print(result["messages"][-1]["content"])
