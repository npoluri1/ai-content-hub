"""
Agent Orchestration with LangGraph — state management, checkpointing, human-in-loop.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint import MemorySaver
from typing import TypedDict, Annotated, Sequence
import operator

class AgentState(TypedDict):
    messages: Annotated[Sequence[dict], operator.add]
    next_agent: str
    human_feedback: str

checkpointer = MemorySaver()

workflow = StateGraph(AgentState)

def router(state: AgentState) -> AgentState:
    last = state["messages"][-1]
    if "tool" in last.get("content", ""):
        state["next_agent"] = "tool_executor"
    elif "retrieve" in last.get("content", ""):
        state["next_agent"] = "rag_retriever"
    else:
        state["next_agent"] = "llm"
    return state

def tool_executor(state: AgentState) -> AgentState:
    state["messages"].append({
        "role": "system",
        "content": f"Executing tool for: {state['messages'][-1]['content']}"
    })
    state["next_agent"] = "llm"
    return state

workflow.add_node("router", router)
workflow.add_node("tool_executor", tool_executor)
workflow.add_edge(START, "router")
workflow.add_conditional_edges(
    "router",
    lambda s: s["next_agent"],
    {"tool_executor": "tool_executor", "rag_retriever": "rag_retriever", "llm": "llm"}
)
workflow.add_edge("tool_executor", END)

app = workflow.compile(checkpointer=checkpointer)
