"""
Final Project: Document Q&A System
A complete CLI-based RAG system with ingestion, interactive Q&A, metadata filtering, and re-ranking.

Usage:
    python app.py --ingest ./sample_docs      # Ingest documents
    python app.py                              # Interactive Q&A mode
    python app.py --query "What is RAG?"       # Single query mode
    python app.py --rerank                     # Enable re-ranking
"""

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


SAMPLE_DIR = Path(__file__).parent / "sample_docs"
PERSIST_DIR = Path(__file__).parent / "chroma_index"
COLLECTION_NAME = "doc_qa"


SAMPLE_DOCS = {
    "rag_intro.txt": """Retrieval-Augmented Generation (RAG) is a technique that combines
retrieval from a knowledge base with text generation from an LLM. It was introduced
by Lewis et al. in 2020. RAG reduces hallucinations by grounding LLM outputs in
retrieved evidence, enables access to up-to-date information, and allows LLMs to
work with private data securely. The pipeline involves chunking documents, embedding
chunks into vectors, storing them in a vector database, retrieving relevant chunks
at query time, and generating answers grounded in those chunks.""",

    "chunking.txt": """Chunking is the process of splitting documents into smaller pieces
for RAG. Common strategies include fixed-size chunking (split by token count),
recursive character splitting (respects paragraph/sentence boundaries), and semantic
chunking (detects topic shifts via embeddings). Key parameters are chunk size
(typically 200-1000 tokens) and chunk overlap (10-20% of chunk size to maintain
boundary coherence). Smaller chunks give higher precision, larger chunks better context.""",

    "embeddings.txt": """Embedding models convert text into dense vector representations.
Popular choices: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions, fast),
text-embedding-3-small (1536 dimensions, OpenAI), BGE-large-en-v1.5 (1024 dims, BAAI).
Higher dimensions capture more nuance but require more storage. Matryoshka embeddings
allow dimension truncation without retraining. The embedding model choice is the
single biggest factor in retrieval quality — a good model beats any algorithmic tweak.""",

    "vector_db.txt": """Vector databases store embeddings and enable similarity search.
ChromaDB is lightweight and embedded, great for prototyping. Pinecone is a managed
cloud service. Weaviate supports hybrid search (vector + BM25 keyword). Qdrant is
Rust-based with high performance. pgvector adds vector search to PostgreSQL.
Most use HNSW (Hierarchical Navigable Small World) graphs for Approximate Nearest
Neighbor search, achieving sub-linear search time by trading a small amount of
accuracy for massive speed gains.""",
}


def setup_sample_docs():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for fname, content in SAMPLE_DOCS.items():
        fpath = SAMPLE_DIR / fname
        if not fpath.exists():
            fpath.write_text(content.strip(), encoding="utf-8")
    count = len(list(SAMPLE_DIR.glob("*.txt")))
    print(f"[setup] {count} sample documents ready in {SAMPLE_DIR}")


def ingest_directory(doc_dir: Path, embed_model, client, collection):
    txt_files = list(doc_dir.glob("*.txt"))
    if not txt_files:
        print(f"[ingest] No .txt files found in {doc_dir}")
        return

    print(f"[ingest] Found {len(txt_files)} .txt files")

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import TextLoader

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400, chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks = []
    for fpath in txt_files:
        loader = TextLoader(str(fpath), encoding="utf-8")
        docs = loader.load()
        chunks = splitter.split_documents(docs)
        now = datetime.now().isoformat()
        for c in chunks:
            c.metadata["source"] = fpath.name
            c.metadata["ingested_at"] = now
            c.metadata["file_size"] = fpath.stat().st_size
        all_chunks.extend(chunks)
        print(f"  {fpath.name}: {len(chunks)} chunks")

    texts = [c.page_content for c in all_chunks]
    ids = [f"{c.metadata['source']}_{i}" for i, c in enumerate(all_chunks)]
    metadatas = [c.metadata for c in all_chunks]

    print(f"[embed] Generating {len(texts)} embeddings...")
    vectors = embed_model.encode(texts, show_progress_bar=True).tolist()

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(COLLECTION_NAME)
    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    print(f"[store] Indexed {len(texts)} chunks from {len(txt_files)} files")


def retrieve(
    query: str, embed_model, collection,
    top_k: int = 5, where_filter: dict = None,
):
    q_vec = embed_model.encode([query]).tolist()
    kwargs = {"query_embeddings": q_vec, "n_results": top_k}
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)
    if not results["documents"] or not results["documents"][0]:
        return []

    docs = results["documents"][0]
    scores = results["distances"][0] if results["distances"] else [0.0] * len(docs)
    metas = results["metadatas"][0]
    return list(zip(docs, scores, metas))


def rerank(query: str, results: list, reranker, top_k: int = 3):
    if not results or reranker is None:
        return results[:top_k]

    pairs = [(query, doc) for doc, _, _ in results]
    cross_scores = reranker.predict(pairs)
    scored = list(zip(results, cross_scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [
        (doc, float(score), meta)
        for (doc, _, meta), score in scored[:top_k]
    ]


def build_prompt(query: str, results: list) -> str:
    context_parts = []
    for doc, score, meta in results:
        header = f"[{meta.get('source', '?')}]"
        context_parts.append(f"{header}\n{doc}")
    context = "\n\n---\n\n".join(context_parts)

    return f"""You are a document Q&A assistant. Answer the question using ONLY the context below.
Cite the source filename for each key claim.

Context:
{context}

Question: {query}

Answer:"""


def generate_answer(prompt: str) -> str:
    """Simulated LLM. Replace with real LLM call when you have an API key."""
    lines = prompt.split("\n")
    in_context = False
    context = []
    for line in lines:
        if line.startswith("Context:"):
            in_context = True
            continue
        if in_context:
            if line.startswith("Question:"):
                break
            if line.strip():
                context.append(line.strip())
    if not context:
        return "I cannot answer this based on the available context."
    preview = "\n".join(context[:4])
    sources = set()
    for line in context:
        if line.startswith("[") and "]" in line:
            src = line[1:line.index("]")]
            sources.add(src)
    source_str = f"\n\nSources: {', '.join(sorted(sources))}" if sources else ""
    return f"Based on the documents:\n\n{preview}{source_str}"


def format_result(doc: str, score: float, meta: dict, width: int = 72):
    src = meta.get("source", "?")
    ingested = meta.get("ingested_at", "?")[:10]
    return (
        f"  [Score: {score:.3f}] [Source: {src}] [Ingested: {ingested}]\n"
        f"  {textwrap.fill(doc, width=width, initial_indent='', subsequent_indent='  ')}"
    )


def interactive_loop(embed_model, collection, reranker=None):
    print("\n" + "=" * 60)
    print("  Document Q&A System")
    print("  Type 'quit' to exit, '/help' for commands")
    print("=" * 60)

    history = []
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input == "/help":
            print("\nCommands:")
            print("  /filter source=<name>   Filter by source file")
            print("  /filter after=<date>    Filter by ingestion date (YYYY-MM-DD)")
            print("  /filter clear           Clear all filters")
            print("  /rerank on              Enable re-ranking")
            print("  /rerank off             Disable re-ranking")
            print("  /status                 Show current settings")
            print("  quit                    Exit")
            continue

        where_clause = {}
        if user_input.startswith("/"):
            parts = user_input.split()
            if parts[0] == "/filter" and len(parts) > 1:
                if parts[1] == "clear":
                    print("[filter] Cleared all filters")
                elif "=" in parts[1]:
                    key, val = parts[1].split("=", 1)
                    if key == "source":
                        where_clause["source"] = val
                        print(f"[filter] Filtering by source = {val}")
                    elif key == "after":
                        where_clause["ingested_at"] = { "$gte": val }
                        print(f"[filter] Filtering by ingested_at >= {val}")
                continue

        history.append({"role": "user", "content": user_input})

        retrieved = retrieve(
            user_input, embed_model, collection,
            top_k=10 if reranker else 5,
            where_filter=where_clause or None,
        )

        if not retrieved:
            print("\nAnswer: I couldn't find any relevant documents.")
            continue

        if reranker:
            retrieved = rerank(user_input, retrieved, reranker, top_k=3)

        print("\n--- Retrieved Sources ---")
        for doc, score, meta in retrieved:
            print(format_result(doc, score, meta))

        prompt = build_prompt(user_input, retrieved)
        answer = generate_answer(prompt)
        print(f"\nAnswer:\n{textwrap.fill(answer, width=72)}")

        history.append({"role": "assistant", "content": answer})


def main():
    parser = argparse.ArgumentParser(description="Document Q&A System")
    parser.add_argument("--ingest", type=str, help="Directory of .txt files to ingest")
    parser.add_argument("--query", type=str, help="Single query (non-interactive)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    parser.add_argument("--rerank", action="store_true", help="Enable cross-encoder re-ranking")
    parser.add_argument("--filter-source", type=str, help="Filter by source filename")
    parser.add_argument("--filter-after", type=str, help="Filter by date (YYYY-MM-DD)")
    args = parser.parse_args()

    PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Document Q&A System")
    print("=" * 60)

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(
        path=str(PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(COLLECTION_NAME)

    # Ingest mode
    if args.ingest:
        setup_sample_docs()
        doc_dir = Path(args.ingest)
        if not doc_dir.exists():
            print(f"[error] Directory not found: {doc_dir}")
            sys.exit(1)
        ingest_directory(doc_dir, embed_model, client, collection)
        print(f"\nIngestion complete. Index stored in {PERSIST_DIR}")
        print("Run without --ingest to start querying.")
        return

    # Ensure there's data
    if collection.count() == 0:
        print("[setup] No index found. Ingesting sample documents...")
        setup_sample_docs()
        ingest_directory(SAMPLE_DIR, embed_model, client, collection)

    # Re-ranker
    reranker = None
    if args.rerank:
        print("[rerank] Loading cross-encoder model...")
        reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        print("[rerank] Ready")

    # Single query mode
    if args.query:
        where_filter = {}
        if args.filter_source:
            where_filter["source"] = args.filter_source
        if args.filter_after:
            where_filter["ingested_at"] = {"$gte": args.filter_after}

        retrieved = retrieve(
            args.query, embed_model, collection,
            top_k=args.top_k * 2 if reranker else args.top_k,
            where_filter=where_filter or None,
        )

        if not retrieved:
            print("No relevant documents found.")
            return

        if reranker:
            retrieved = rerank(args.query, retrieved, reranker, top_k=args.top_k)

        print(f"\nQuery: {args.query}")
        print(f"\nRetrieved {len(retrieved)} chunks:\n")
        for doc, score, meta in retrieved:
            print(format_result(doc, score, meta))

        prompt = build_prompt(args.query, retrieved)
        answer = generate_answer(prompt)
        print(f"\n{textwrap.fill(answer, width=72)}")
        return

    # Interactive mode
    interactive_loop(embed_model, collection, reranker)


if __name__ == "__main__":
    main()
