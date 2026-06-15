"""
Example 3: RAG with Cross-Encoder Re-Ranking
Retrieve more chunks, re-rank with a cross-encoder, then generate.

Why re-rank?
- Initial vector search is fast but imperfect (ANN trade-offs)
- Cross-encoder scores query-chunk pairs with full attention (slower but accurate)
- Retrieve top-10, re-rank to top-3: precision of dense search + accuracy of cross-encoder

Usage:
    python rag_with_rerank.py
    python rag_with_rerank.py --query "What are embeddings?" --retrieve-k 10 --rerank-k 3
"""

import argparse
import textwrap
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from chromadb.config import Settings


SAMPLE_CONTENT = """
Retrieval-Augmented Generation (RAG) combines retrieval from a knowledge base
with text generation. The core idea is simple: when a user asks a question,
first find relevant documents, then feed them to an LLM as context.

RAG pipelines have several critical design decisions that affect quality:

Chunking Strategy: How you split documents matters. RecursiveCharacterTextSplitter
splits on natural boundaries like paragraphs and sentences. Semantic chunking
groups sentences by topic similarity. The chunk size affects retrieval precision
-- smaller chunks give more precise matches but may lack surrounding context.

Embedding Model Choice: The embedding model determines what "similar" means.
all-MiniLM-L6-v2 is fast and small (384 dims). OpenAI's text-embedding-3-large
(3072 dims) captures more nuance. BGE-large-en-v1.5 (1024 dims) performs well
on retrieval benchmarks. The best model depends on your domain and language.

Retrieval Methods: Simple vector similarity is the baseline. Hybrid search
combines vector + keyword (BM25) for better term matching. Multi-vector retrieval
uses separate embeddings for different query types. Query expansion generates
multiple query variants to improve recall.

Re-Ranking: After initial retrieval, a cross-encoder re-ranker scores each
query-chunk pair with full attention. This is more accurate than the bi-encoder
used in initial retrieval but too slow for large-scale search. Typical pattern:
retrieve top-20 with bi-encoder, re-rank top-5 with cross-encoder.

Context Window Management: Retrieved chunks must fit in the LLM's context window.
Strategies include: truncating chunks to fit, summarizing chunks before insertion,
and compressing multiple chunks into a single summary. The goal is to maximize
relevant information while staying within token limits.

Evaluation: RAG quality is measured by faithfulness, answer relevance, and
context precision. RAGAS provides automated evaluation. Key metrics include
context recall (are all needed facts retrieved?) and answer faithfulness
(does the answer contradict the context?).
"""


def ensure_sample_doc(path: Path):
    if not path.exists():
        path.write_text(SAMPLE_CONTENT.strip(), encoding="utf-8")
        print(f"[setup] Created sample document: {path}")
    else:
        print(f"[setup] Using existing document: {path}")


def load_and_chunk(path: Path, chunk_size: int = 200, chunk_overlap: int = 20):
    loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"[ingest] Split into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
    return chunks


def store_chunks(chunks, embed_model, collection):
    texts = [c.page_content for c in chunks]
    ids = [str(i) for i in range(len(chunks))]
    metadatas = [c.metadata for c in chunks]

    print(f"[embed] Generating {len(texts)} embeddings...")
    vectors = embed_model.encode(texts, show_progress_bar=True).tolist()
    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)
    print(f"[store] Stored {len(texts)} chunks in ChromaDB")
    return texts


def retrieve(query: str, embed_model, collection, top_k: int = 10):
    q_vec = embed_model.encode([query]).tolist()
    results = collection.query(query_embeddings=q_vec, n_results=min(top_k, collection.count()))
    docs = results["documents"][0]
    scores = results["distances"][0] if results["distances"] else [0.0] * len(docs)
    return list(zip(docs, scores))


def rerank(query: str, chunks_with_scores: list, reranker, top_k: int = 3):
    print(f"[rerank] Re-ranking {len(chunks_with_scores)} chunks with cross-encoder...")
    pairs = [(query, doc) for doc, _ in chunks_with_scores]
    if not pairs:
        return chunks_with_scores[:top_k]

    cross_scores = reranker.predict(pairs)

    scored = list(zip(chunks_with_scores, cross_scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    reranked = [(doc, float(score)) for (doc, _orig_score), score in scored]

    print(f"[rerank] Top-{top_k} after re-ranking:")
    for i, (doc, score) in enumerate(reranked[:top_k]):
        print(f"  [{i+1}] cross-score={score:.4f}: {doc[:80].replace(chr(10), ' ')}...")

    return reranked[:top_k]


def generate_answer(query: str, retrieved: list) -> str:
    context = "\n\n---\n\n".join(doc for doc, _ in retrieved)
    prompt = f"""Answer the question based ONLY on the context below.

Context:
{context}

Question: {query}

Answer:"""
    return prompt


def simulate_llm(prompt: str) -> str:
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
    answer = "\n".join(context[:3])
    return answer if answer else "I cannot answer this based on the available context."


def main():
    parser = argparse.ArgumentParser(description="RAG with cross-encoder re-ranking")
    parser.add_argument("--query", default="How does chunking strategy affect RAG quality?")
    parser.add_argument("--retrieve-k", type=int, default=10, help="Number of chunks to retrieve initially")
    parser.add_argument("--rerank-k", type=int, default=3, help="Number of chunks to keep after re-ranking")
    args = parser.parse_args()

    persist_dir = Path(__file__).parent / "chroma_rerank"
    doc_path = persist_dir / "sample_doc.txt"
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    # Setup
    ensure_sample_doc(doc_path)
    chunks = load_and_chunk(doc_path, chunk_size=200, chunk_overlap=20)

    # Embed & store
    print("\n" + "=" * 60)
    print("Embedding & Storing")
    print("=" * 60)
    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection("rag_rerank")
    except Exception:
        pass
    collection = client.get_or_create_collection("rag_rerank")

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    store_chunks(chunks, embed_model, collection)

    # Retrieve (wide net)
    print("\n" + "=" * 60)
    print(f"INITIAL RETRIEVAL (top-{args.retrieve_k})")
    print("=" * 60)
    retrieved = retrieve(args.query, embed_model, collection, top_k=args.retrieve_k)

    if not retrieved:
        print("No documents retrieved. Check the document content.")
        return

    print(f"\nQuery: {args.query}")
    print(f"Retrieved {len(retrieved)} chunks (pre-rerank):")
    for i, (doc, score) in enumerate(retrieved):
        print(f"  [{i+1}] vec-score={score:.4f}: {doc[:80].replace(chr(10), ' ')}...")

    # Re-rank
    print("\n" + "=" * 60)
    print("CROSS-ENCODER RE-RANKING")
    print("=" * 60)
    print("Loading cross-encoder (ms-marco-MiniLM-L-6-v2)...")
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    reranked = rerank(args.query, retrieved, reranker, top_k=args.rerank_k)

    # Generate
    print("\n" + "=" * 60)
    print("GENERATION (from re-ranked chunks)")
    print("=" * 60)
    prompt = generate_answer(args.query, reranked)
    answer = simulate_llm(prompt)
    print(f"\n{textwrap.fill(answer, width=70)}")

    # Compare: what would top-3 without re-ranking look like?
    print("\n" + "-" * 60)
    print("COMPARISON")
    print("-" * 60)
    no_rerank = retrieved[:args.rerank_k]
    print(f"\nTop-{args.rerank_k} WITHOUT re-ranking:")
    for doc, score in no_rerank:
        print(f"  vec-score={score:.4f}: {doc[:80].replace(chr(10), ' ')}...")
    print(f"\nTop-{args.rerank_k} WITH re-ranking:")
    for doc, score in reranked:
        print(f"  cross-score={score:.4f}: {doc[:80].replace(chr(10), ' ')}...")

    print("\nRe-ranking typically improves precision by 10-25% in retrieval benchmarks.")


if __name__ == "__main__":
    main()
