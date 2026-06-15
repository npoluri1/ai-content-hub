"""
Example 2: RAG with Metadata Filtering
Add source, date, category metadata to chunks, then filter during retrieval.

Usage:
    python rag_with_metadata.py
    python rag_with_metadata.py --filter '{"source": "docs"}' --query "chunking strategies"
"""

import argparse
import json
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
import random
import string

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


SAMPLE_CONTENT = """
Document 001: Chunking Strategies

Chunking is the process of splitting documents into smaller pieces for RAG.
Common approaches include fixed-size chunking where you split by token count,
recursive character splitting that respects natural boundaries like paragraphs
and sentences, and semantic chunking that detects topic shifts using embeddings.

The choice of chunking strategy significantly impacts retrieval quality.
Smaller chunks (100-200 tokens) give higher precision but may lack context.
Larger chunks (500-1000 tokens) provide better context but can dilute relevance.
A chunk overlap of 10-20% helps maintain boundary coherence.
"""

SAMPLE_CONTENT_2 = """
Document 002: Embedding Models

Embedding models convert text into dense vector representations for similarity search.
Popular choices include OpenAI's text-embedding-3-small (1536 dimensions),
sentence-transformers/all-MiniLM-L6-v2 (384 dimensions), and BAAI's BGE models.

The embedding dimension affects storage size and search speed. Higher dimensions
generally capture more nuance but require more storage. Recent research shows that
Matryoshka embeddings allow truncating dimensions without major quality loss.
"""

SAMPLE_CONTENT_3 = """
Document 003: Vector Databases

Vector databases store embeddings and enable efficient similarity search.
ChromaDB is popular for prototyping. Pinecone offers managed cloud service.
Weaviate supports hybrid search with both vector and keyword matching.
Qdrant is known for high performance with filtering at scale.

Most vector databases support Approximate Nearest Neighbor (ANN) search using
algorithms like HNSW (Hierarchical Navigable Small World) for sub-linear search time.
"""

SAMPLE_CONTENT_4 = """
Document 004: Evaluation Metrics

RAG quality is measured by metrics like faithfulness (does the answer match the context?),
answer relevance (does the answer address the question?), and context precision
(how much of the context was actually useful). Tools like RAGAS provide automated
evaluation frameworks that score these dimensions without human annotation.

One important consideration is that evaluation requires a test dataset with
ground-truth answers. Human evaluation remains the gold standard but is expensive.
LLM-based evaluation (using a strong model like GPT-4 to judge) offers a reasonable
approximation at lower cost.
"""


DOCUMENTS = {
    "docs": [
        (SAMPLE_CONTENT, "2024-06-01", "chunking"),
        (SAMPLE_CONTENT_2, "2024-07-15", "embeddings"),
        (SAMPLE_CONTENT_3, "2024-08-20", "vector_db"),
    ],
    "blog": [
        (SAMPLE_CONTENT_4, "2025-01-10", "evaluation"),
    ],
}


def create_multi_source_docs(base_dir: Path):
    for source, entries in DOCUMENTS.items():
        for i, (content, date_str, category) in enumerate(entries):
            fname = f"{source}_{category}_{i}.txt"
            fpath = base_dir / fname
            if not fpath.exists():
                fpath.write_text(content.strip())
    print(f"[setup] Created {sum(len(v) for v in DOCUMENTS.values())} multi-source documents in {base_dir}")


def load_and_chunk_with_metadata(base_dir: Path, chunk_size=300, chunk_overlap=30):
    all_chunks = []
    for source, entries in DOCUMENTS.items():
        for i, (content, date_str, category) in enumerate(entries):
            fname = f"{source}_{category}_{i}.txt"
            fpath = base_dir / fname
            loader = TextLoader(str(fpath), encoding="utf-8")
            docs = loader.load()
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            chunks = splitter.split_documents(docs)
            for c in chunks:
                c.metadata["source"] = source
                c.metadata["date"] = date_str
                c.metadata["category"] = category
            all_chunks.extend(chunks)
    print(f"[ingest] Loaded and chunked {len(all_chunks)} chunks with metadata")
    return all_chunks


def store_chunks(chunks, embed_model, collection):
    texts = [c.page_content for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [c.metadata for c in chunks]

    print(f"[embed] Generating {len(texts)} embeddings...")
    vectors = embed_model.encode(texts, show_progress_bar=True).tolist()

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    print(f"[store] Stored {len(texts)} chunks with metadata filters: source, date, category")


def retrieve(query: str, embed_model, collection, top_k: int = 3, where_filter: dict = None):
    q_vec = embed_model.encode([query]).tolist()
    kwargs = {"query_embeddings": q_vec, "n_results": top_k}
    if where_filter:
        kwargs["where"] = where_filter
        filter_desc = json.dumps(where_filter)
    else:
        filter_desc = "none"

    results = collection.query(**kwargs)
    docs = results["documents"][0]
    scores = results["distances"][0] if results["distances"] else [0] * len(docs)
    metas = results["metadatas"][0]
    print(f"[retrieve] top-{top_k} with filter={filter_desc}")
    return list(zip(docs, scores, metas))


def generate_answer(query: str, retrieved: list) -> str:
    context_parts = []
    for doc, score, meta in retrieved:
        header = f"[Source: {meta.get('source','?')} | Date: {meta.get('date','?')} | Category: {meta.get('category','?')}]"
        context_parts.append(f"{header}\n{doc}")
    context = "\n\n---\n\n".join(context_parts)
    prompt = f"""Answer the question using ONLY the context below. Cite the source for each claim.

Context:
{context}

Question: {query}

Answer:"""
    return prompt


def simulate_llm(prompt: str) -> str:
    lines = prompt.split("\n")
    reading_context = False
    context_lines = []
    for line in lines:
        if line.startswith("Context:"):
            reading_context = True
            continue
        if reading_context:
            if line.startswith("Question:"):
                break
            if line.strip():
                context_lines.append(line.strip())
    answer = "\n".join(context_lines[:4])
    return answer if answer else "I cannot answer this based on the available context."


def main():
    parser = argparse.ArgumentParser(description="RAG with metadata filtering")
    parser.add_argument("--query", default="What are chunking strategies?")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--filter",
        default=None,
        help='Metadata filter as JSON, e.g. \'{"source": "docs"}\'',
    )
    args = parser.parse_args()

    persist_dir = Path(__file__).parent / "chroma_metadata"
    docs_dir = persist_dir / "source_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    create_multi_source_docs(docs_dir)

    print("=" * 60)
    print("Ingesting multi-source documents with metadata")
    print("=" * 60)
    chunks = load_and_chunk_with_metadata(docs_dir)

    print("\n" + "=" * 60)
    print("Embedding & Storing in ChromaDB")
    print("=" * 60)
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection("rag_with_metadata")
    except Exception:
        pass
    collection = client.get_or_create_collection("rag_with_metadata")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    store_chunks(chunks, embed_model, collection)

    # --- Query without filter ---
    print("\n" + "=" * 60)
    print(f"QUERY (no filter): {args.query}")
    print("=" * 60)
    retrieved = retrieve(args.query, embed_model, collection, top_k=args.top_k)
    for doc, score, meta in retrieved:
        print(f"\n  score={score:.4f} | src={meta['source']} | cat={meta['category']}")
        print(f"  {doc[:100].replace(chr(10), ' ')}...")

    # --- Query WITH filter (if provided) ---
    if args.filter:
        where_filter = json.loads(args.filter)
        print("\n" + "=" * 60)
        print(f"QUERY (with filter {args.filter}): {args.query}")
        print("=" * 60)
        retrieved = retrieve(args.query, embed_model, collection, top_k=args.top_k, where_filter=where_filter)
        for doc, score, meta in retrieved:
            print(f"\n  score={score:.4f} | src={meta['source']} | cat={meta['category']}")
            print(f"  {doc[:100].replace(chr(10), ' ')}...")

    # --- Generate answer from unfiltered results ---
    print("\n" + "=" * 60)
    print("GENERATED ANSWER (using unfiltered results)")
    print("=" * 60)
    prompt = generate_answer(args.query, retrieved)
    answer = simulate_llm(prompt)
    print(f"\n{textwrap.fill(answer, width=70)}")

    print("\n" + "-" * 60)
    print("Try filtering by source:")
    print('  python rag_with_metadata.py --filter \'{"source": "docs"}\'')
    print('  python rag_with_metadata.py --filter \'{"category": "embeddings"}\'')
    print("-" * 60)


if __name__ == "__main__":
    main()
