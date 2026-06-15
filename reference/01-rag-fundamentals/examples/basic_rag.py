"""
Example 1: Basic RAG Pipeline
Full ingest -> chunk -> embed -> store -> retrieve -> generate flow.

Usage:
    python basic_rag.py                          # Run with sample document
    python basic_rag.py --doc path/to/file.txt   # Run with your own document
"""

import argparse
import os
import textwrap
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


SAMPLE_CONTENT = """
Retrieval-Augmented Generation (RAG) is a technique that combines retrieval
from a knowledge base with text generation. It was introduced by Lewis et al.
in 2020 in the paper "Retrieval-Augmented Generation for Knowledge-Intensive
NLP Tasks".

The key insight of RAG is that instead of relying solely on an LLM's
parametric memory (its training data), we can retrieve relevant documents
from an external knowledge base and use them as context for generation.

RAG has several important advantages:
1. It reduces hallucinations by grounding answers in retrieved evidence.
2. It enables access to up-to-date information without retraining.
3. It allows LLMs to work with private or proprietary data securely.
4. It provides source attribution, making answers verifiable.

The typical RAG pipeline works as follows:
- Documents are split into chunks (chunking).
- Each chunk is converted to a vector embedding (embedding).
- Vectors are stored in a vector database (indexing).
- At query time, the question is embedded and similar chunks are retrieved
  (retrieval).
- The retrieved chunks are inserted into the LLM prompt as context
  (augmentation).
- The LLM generates an answer grounded in the provided context (generation).

Common chunking strategies include:
- Fixed-size chunking: Split by a fixed number of tokens.
- Recursive character splitting: Split on natural boundaries like paragraphs.
- Semantic chunking: Split where topic shifts occur.

Embedding models convert text into dense vector representations.
Popular choices include:
- sentence-transformers/all-MiniLM-L6-v2 (384 dimensions, fast)
- text-embedding-3-small (1536 dimensions, OpenAI)
- BGE embeddings from BAAI (1024 dimensions, strong performance)

Vector databases for RAG include:
- ChromaDB: Lightweight, embedded, good for prototyping.
- Pinecone: Managed cloud service, high scale.
- Weaviate: Open-source, hybrid search support.
- Qdrant: Rust-based, high performance.
- pgvector: PostgreSQL extension, good for existing Postgres users.

Retrieval quality depends on:
- Embedding model quality.
- Chunk size and strategy.
- Number of chunks retrieved (top-k).
- Metadata filtering.
- Re-ranking with cross-encoders.

RAG is widely used in customer support chatbots, internal knowledge base
search, legal document analysis, medical research assistance, and more.
"""


def ensure_sample_doc(path: Path):
    if not path.exists():
        path.write_text(SAMPLE_CONTENT.strip(), encoding="utf-8")
        print(f"[setup] Created sample document: {path}")
    else:
        print(f"[setup] Using existing document: {path}")


def load_and_chunk(path: Path, chunk_size: int = 500, chunk_overlap: int = 50):
    loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"[ingest] Loaded 1 document, split into {len(chunks)} chunks")
    return chunks


def embed_and_store(chunks, embed_model, collection, persist_dir: Path):
    texts = [c.page_content for c in chunks]
    ids = [str(i) for i in range(len(chunks))]
    metadatas = [c.metadata for c in chunks]

    print(f"[embed] Generating {len(texts)} embeddings...")
    vectors = embed_model.encode(texts, show_progress_bar=True).tolist()

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    print(f"[store] Stored {len(texts)} chunks in ChromaDB @ {persist_dir}")
    return texts


def retrieve(query: str, embed_model, collection, top_k: int = 3):
    q_vec = embed_model.encode([query]).tolist()
    results = collection.query(query_embeddings=q_vec, n_results=top_k)
    docs = results["documents"][0]
    scores = results["distances"][0] if results["distances"] else [0] * len(docs)
    return list(zip(docs, scores))


def generate(query: str, retrieved_chunks: list) -> str:
    context = "\n\n---\n\n".join(chunk for chunk, _ in retrieved_chunks)
    prompt = f"""You are a helpful assistant. Answer the question based ONLY on the context below.
If the context doesn't contain the answer, say "I cannot answer this based on the available context."

Context:
{context}

Question: {query}

Answer:"""
    return prompt


def simulate_llm(prompt: str) -> str:
    """Simulates an LLM response by extracting relevant-sounding sentences
    from the prompt's context section. Replace this with an actual LLM call
    when you have an API key."""
    lines = prompt.split("\n")
    context_start = False
    context_lines = []
    for line in lines:
        if line.startswith("Context:"):
            context_start = True
            continue
        if context_start:
            if line.startswith("Question:"):
                break
            if line.strip():
                context_lines.append(line.strip())
    answer = "\n".join(context_lines[:3])
    return answer if answer else "I cannot answer this based on the available context."


def main():
    parser = argparse.ArgumentParser(description="Basic RAG Pipeline")
    parser.add_argument("--doc", default=None, help="Path to input document")
    parser.add_argument("--query", default="What is RAG and why is it useful?")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    persist_dir = Path(__file__).parent / "chroma_basic"
    doc_path = Path(args.doc) if args.doc else persist_dir / "sample_doc.txt"
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Ingest
    print("=" * 60)
    print("STEP 1: Ingestion")
    print("=" * 60)
    ensure_sample_doc(doc_path)
    chunks = load_and_chunk(doc_path)

    # 2. Embed & Store
    print("\n" + "=" * 60)
    print("STEP 2: Embedding & Storage")
    print("=" * 60)
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection("rag_docs")
    except Exception:
        pass
    collection = client.get_or_create_collection("rag_docs")

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    embed_and_store(chunks, embed_model, collection, persist_dir)

    # 3. Retrieve
    print("\n" + "=" * 60)
    print(f"STEP 3: Retrieval (top-{args.top_k})")
    print("=" * 60)
    print(f"Query: {args.query}")
    retrieved = retrieve(args.query, embed_model, collection, top_k=args.top_k)
    for i, (doc, score) in enumerate(retrieved):
        preview = doc[:120].replace("\n", " ")
        print(f"\n  [{i+1}] score={score:.4f}: {preview}...")

    # 4. Generate
    print("\n" + "=" * 60)
    print("STEP 4: Generation")
    print("=" * 60)
    prompt = generate(args.query, retrieved)
    answer = simulate_llm(prompt)
    print(f"\nAnswer:\n{textwrap.fill(answer, width=70)}")

    # Show the full prompt (for learning)
    print("\n" + "-" * 60)
    print("Full prompt sent to LLM:")
    print("-" * 60)
    print(prompt[:600])
    print("...")

    print("\nBasic RAG pipeline complete. Try your own queries with --query.")


if __name__ == "__main__":
    main()
