"""
Checkpointing demo — pause, inspect, correct, and resume mid-run.
"""
from langgraph.checkpoint import MemorySaver
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class State(TypedDict):
    value: int
    status: str

checkpointer = MemorySaver()

builder = StateGraph(State)
builder.add_node("step_1", lambda s: {"value": s["value"] + 1, "status": "step_1_done"})
builder.add_node("step_2", lambda s: {"value": s["value"] * 2, "status": "step_2_done"})
builder.add_edge(START, "step_1")
builder.add_edge("step_1", "step_2")
builder.add_edge("step_2", END)

app = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "demo-1"}}

for event in app.stream({"value": 1, "status": "start"}, config):
    print(f"Step: {event}")

state = app.get_state(config)
print(f"Resumed state: {state.values}")

# Modify mid-run
app.update_state(config, {"value": 100})
resumed = app.get_state(config)
print(f"After correction: {resumed.values}")
