# Final Project: Document Q&A System

A complete CLI-based RAG system that ingests documents, builds a searchable index, and answers questions interactively.

## Features

- **Ingest** all `.txt` files from a directory
- **Metadata** tracking (filename, date ingested, file size)
- **Interactive Q&A** loop with history
- **Metadata filtering** by source file and date range
- **Re-ranking** mode for higher precision
- **Source citations** with every answer

## Quick Start

```bash
# 1. Ingest documents
python app.py --ingest ./sample_docs

# 2. Start interactive querying
python app.py
```

## Commands

| Command | Description |
|---------|-------------|
| `--ingest <dir>` | Ingest all `.txt` files from `<dir>` into ChromaDB |
| `--query "..."` | Single query mode (non-interactive) |
| `--rerank` | Enable cross-encoder re-ranking |
| `--filter-source "name.txt"` | Only retrieve from a specific source file |
| `--filter-after "2024-01-01"` | Only retrieve chunks ingested after this date |

## Interactive Mode

When run without arguments, starts an interactive loop:

```
Document Q&A System
Type 'quit' to exit, '/help' for commands

You: What is RAG?
```

## Sample Documents

The `sample_docs/` directory contains 4 documents about RAG topics ready for testing:

1. `rag_intro.txt` — Overview of RAG
2. `chunking.txt` — Chunking strategies
3. `embeddings.txt` — Embedding models
4. `vector_db.txt` — Vector databases
