# 01 - Vibe Coding vs Production AI

Core insight from LinkedIn: The $0 stack works for demos. Production requires 4 key decisions.

## The Stack

| Layer | Vibe Version | Production Version |
|-------|-------------|-------------------|
| LLM | Ollama (local) | Llama 3.3 70B / Gemma 4 26B MoE |
| Orchestrator | LangGraph (basic) | LangGraph + checkpointing |
| Vector Store | ChromaDB | ChromaDB + indexing strategy |
| Tool Layer | MCP (direct) | MCP + isolation + RBAC |
| Observability | Langfuse (post-hoc) | Langfuse (day 1, self-hosted) |

## The 4 Decisions

1. **Hardware honesty** — know your RAM/GPU requirements
2. **State management** — LangGraph checkpointing for pause/inspect/resume
3. **Data isolation before MCP** — RBAC, query governors
4. **Observability day 1** — full traces across every node
