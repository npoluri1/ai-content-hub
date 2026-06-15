# 01 — RAG Fundamentals

## What is RAG?

**Retrieval-Augmented Generation (RAG)** is a pattern that enhances LLM outputs by grounding them in external data. Instead of relying solely on the model's training data, RAG retrieves relevant documents from a knowledge base and injects them into the LLM's context at query time.

```
User Query
    │
    ▼
┌─────────────────────┐
│  1. Embed query     │
│  (sentence-transform)│
└─────────┬───────────┘
          │ vector
          ▼
┌─────────────────────┐
│  2. Retrieve top-k  │
│  (ChromaDB / vector │
│   similarity search)│
└─────────┬───────────┘
          │ relevant chunks
          ▼
┌─────────────────────┐
│  3. Augment prompt  │
│  (query + chunks =  │
│   context-rich prompt│)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  4. Generate        │
│  (LLM answers with  │
│   retrieved context)│
└─────────────────────┘
```

### Why RAG?

| Problem | RAG Solution |
|---------|-------------|
| LLM has outdated knowledge | Retrieve from your latest docs |
| LLM hallucinates facts | Constrain answer to retrieved evidence |
| LLM doesn't know your private data | Plug in internal docs without retraining |
| One-size-fits-all responses | Retrieve user-specific context |

### Key Components

| Component | Role | In This Tutorial |
|-----------|------|-----------------|
| **Documents** | Raw source material | Sample text files |
| **Chunker** | Splits docs into searchable pieces | LangChain `RecursiveCharacterTextSplitter` |
| **Embeddings** | Converts text to vectors | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector Store** | Stores + searches vectors | ChromaDB |
| **Retriever** | Finds relevant chunks | ChromaDB similarity search |
| **LLM** | Generates final answer | OpenAI / local model |
| **Re-ranker** *(optional)* | Re-scores retrieved chunks | Cross-encoder model |

---

## The RAG Pipeline — Step by Step

### Step 1: Ingestion
Load documents from raw sources (PDFs, text files, web pages). Clean and normalize the text.

### Step 2: Chunking
Split long documents into smaller pieces (chunks). Good chunking balances:
- **Too small** → loses context
- **Too large** → dilutes relevance
- **Overlap** → preserves boundary context

### Step 3: Embedding
Convert each chunk into a dense vector using an embedding model. Similar chunks map to nearby points in vector space.

### Step 4: Storage
Store vectors in ChromaDB along with the original text and metadata (source, page number, date, etc.).

### Step 5: Retrieval
At query time:
1. Embed the user's question
2. Search ChromaDB for the most similar vectors
3. Return the top-k chunks with their metadata

### Step 6: Augmentation
Build a prompt that includes:
- System instruction
- Retrieved chunks as context
- User's question

### Step 7: Generation
Send the augmented prompt to an LLM. The model answers based on the provided context.

---

## Code Examples

| # | Example | What It Teaches |
|---|---------|-----------------|
| 1 | [`examples/basic_rag.py`](examples/basic_rag.py) | Full ingest → retrieve → generate pipeline |
| 2 | [`examples/rag_with_metadata.py`](examples/rag_with_metadata.py) | Add + filter by metadata (source, date, tags) |
| 3 | [`examples/rag_with_rerank.py`](examples/rag_with_rerank.py) | Improve accuracy with cross-encoder re-ranking |

### Prerequisites

```bash
pip install chromadb sentence-transformers langchain langchain-community
```

For LLM generation (pick one):
```bash
pip install openai          # OpenAI / any OpenAI-compatible API
# OR
pip install transformers     # Local model (slower, free)
# OR
pip install ollama           # Ollama local models
```

### Run Any Example

```bash
cd reference/01-rag-fundamentals
python examples/basic_rag.py
```

All examples auto-create a sample document if none exists, so they work out of the box.

---

## Business Use Cases

| Industry | Use Case | Why RAG |
|----------|----------|---------|
| **Customer Support** | Answer product questions from documentation | Always up-to-date, reduces ticket volume |
| **Healthcare** | Clinicians query medical literature + patient records | Evidence-based answers, privacy-controlled |
| **Legal** | Search case law + contracts for relevant precedents | Hours → seconds, higher recall |
| **E-commerce** | Product catalog Q&A ("which laptop has 32GB?") | Natural language over structured data |
| **Education** | Students query lecture notes + textbooks | Personalized tutoring, no hallucination |
| **Engineering** | Internal codebase + API docs search | Onboard faster, find answers instantly |
| **Finance** | Analyst queries quarterly reports + filings | Data stays current, answers cite sources |
| **HR** | Employee handbook + policy Q&A | Consistent answers, 24/7 self-service |

> See [USE_CASES.md](USE_CASES.md) for 15 detailed business ideas with implementation sketches.

---

## Final Project

**`final_project/`** — A complete Document Q&A System that:
- Ingests all `.txt` files from a configurable directory
- Builds a ChromaDB index with metadata
- Provides an interactive CLI query loop
- Supports metadata filtering (`--source`, `--after-date`)
- Optional re-ranking mode (`--rerank`)
- Shows source citations with each answer

```bash
cd reference/01-rag-fundamentals/final_project
python app.py --ingest ./my_docs
python app.py --query "What is RAG?"
```

See [`final_project/README.md`](final_project/README.md) for full details.

---

## Next Sessions

| # | Topic |
|---|-------|
| 02 | LangGraph Agents — state machines, tool calling, multi-step reasoning |
| 03 | MCP (Model Context Protocol) — standardized tool interfaces |
| 04 | Advanced RAG — query rewriting, multi-hop, agentic RAG |
| 05 | Evaluation — RAGAS, relevance scoring, regression testing |
