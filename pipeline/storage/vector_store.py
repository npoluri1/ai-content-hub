"""ChromaDB vector store — embedding, dedup, and similarity search."""

from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem
import os
import hashlib


class VectorStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.CHROMA_DB_PATH
        os.makedirs(self.db_path, exist_ok=True)
        self._client = None
        self._collection = None
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.db_path)
            self._collection = self._client.get_or_create_collection(
                name="content_hub",
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            print("  [VectorStore] chromadb not installed. pip install chromadb")
            self._client = None

    @property
    def collection(self):
        if self._collection is None:
            self._init_chroma()
        return self._collection

    _embedding_model = None

    def _get_embedding(self, text: str) -> list[float]:
        try:
            if self._embedding_model is None:
                from sentence_transformers import SentenceTransformer
                self.__class__._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            return self._embedding_model.encode(text).tolist()
        except ImportError:
            print("  [VectorStore] sentence-transformers not installed")
            return [0.0] * 384

    def store_items(self, items: list[ContentItem | ClassifiedItem]):
        if self.collection is None:
            print("  [VectorStore] Skipping — ChromaDB unavailable")
            return

        existing_ids = set()
        try:
            existing = self.collection.get(limit=100000)
            existing_ids = set(existing["ids"])
        except:
            pass

        seen_ids = set()
        to_add = []
        for item in items:
            if item.id in existing_ids or item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            text = f"{item.title}\n{item.content_cleaned}"
            to_add.append(item)

            if len(to_add) >= 100:
                self._batch_store(to_add)
                to_add = []

        if to_add:
            self._batch_store(to_add)

    def _batch_store(self, items: list):
        ids = [it.id for it in items]
        texts = [f"{it.title}\n{it.content_cleaned}" for it in items]
        metadatas = [{
            "source": it.source,
            "source_type": it.source_type,
            "topics": ",".join(it.topics),
            "author": it.author_name,
            "url": it.url,
            "engagement": it.engagement,
            "published_at": str(it.published_at) if it.published_at else "",
            "title": it.title[:200],
        } for it in items]

        try:
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
            )
        except Exception as e:
            # Fallback: compute embeddings locally
            embeddings = [self._get_embedding(t) for t in texts]
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts,
            )

    def search(self, query: str, n_results: int = 10, filter_source: str = None) -> list[dict]:
        if self.collection is None:
            return []

        where = {}
        if filter_source:
            where["source"] = filter_source

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where if where else None,
            )
        except:
            emb = self._get_embedding(query)
            results = self.collection.query(
                query_embeddings=[emb],
                n_results=n_results,
                where=where if where else None,
            )

        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i][:500],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else 0,
            })
        return output

    def search_by_topic(self, topic: str, n_results: int = 20) -> list[dict]:
        if self.collection is None:
            return []
        results = self.collection.get(
            where={"topics": {"$contains": topic}},
            limit=n_results,
        )
        output = []
        for i in range(len(results["ids"])):
            output.append({
                "id": results["ids"][i],
                "content": results["documents"][i][:500],
                "metadata": results["metadatas"][i],
            })
        return output

    def get_recent(self, limit: int = 50) -> list[dict]:
        if self.collection is None:
            return []
        results = self.collection.get(limit=limit)
        output = []
        for i in range(len(results["ids"])):
            output.append({
                "id": results["ids"][i],
                "content": results["documents"][i][:500],
                "metadata": results["metadatas"][i],
            })
        return output

    def count(self) -> int:
        if self.collection is None:
            return 0
        return self.collection.count()
