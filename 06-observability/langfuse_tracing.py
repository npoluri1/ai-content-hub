"""
Observability with Langfuse — trace every LangGraph node, RAG retrieval, and MCP call.
"""

from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
import os

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)

@observe()
def orchestrator_route(user_input: str):
    langfuse_context.update_current_observation(
        name="orchestrator_route",
        input=user_input,
        metadata={"agent": "main", "version": "1.0"}
    )
    if len(user_input) > 50:
        return "rag"
    return "llm"

@observe()
def rag_retrieve(query: str):
    trace_id = langfuse_context.get_current_trace_id()
    langfuse.trace(
        id=trace_id,
        name="rag_retrieval",
        metadata={"query": query, "chunks_retrieved": 4}
    )
    return ["chunk_1", "chunk_2", "chunk_3", "chunk_4"]

@observe()
def llm_call(prompt: str):
    generation = langfuse.generation(
        name="llm_response",
        model="gpt-4o",
        input=prompt,
        output="Simulated response",
        usage={"input": len(prompt), "output": 50}
    )
    return generation.output

route = orchestrator_route("Tell me about LangGraph checkpointing")
if route == "rag":
    chunks = rag_retrieve("LangGraph checkpointing")
result = llm_call("Summarize the retrieved chunks")
print(f"Trace completed. Result: {result}")
