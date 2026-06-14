"""Unsupervised content clustering with multiple methods and fallbacks."""

from ..core.models import ContentItem
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
import math
import os
import pickle
import re
import string


STOP_WORDS = set([
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "have", "been", "some", "same",
    "also", "than", "then", "them", "they", "this", "that", "with", "will", "what",
    "which", "when", "where", "who", "how", "much", "many", "each", "every", "very",
    "just", "about", "into", "over", "such", "only", "other", "more", "most", "some",
    "these", "those", "could", "would", "should", "after", "before", "between", "through", "during",
    "because", "from", "were", "been", "being", "does", "done", "doing", "its", "itself",
    "your", "yours", "yourself", "myself", "himself", "herself", "itself", "ourselves", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "would", "should", "could", "may", "might", "shall",
    "can", "need", "dare", "ought", "used", "must", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "several", "some", "any",
    "no", "none", "most", "much", "many", "more", "less", "fewer", "enough", "too",
    "very", "so", "quite", "rather", "pretty", "almost", "nearly", "really", "just", "barely",
    "hardly", "scarcely", "nearly", "only", "even", "still", "already", "yet", "again", "also",
    "too", "as", "well", "indeed", "surely", "certainly", "definitely", "absolutely", "obviously", "clearly",
    "simply", "merely", "purely", "truly", "likely", "probably", "possibly", "maybe", "perhaps", "please",
    "let", "us", "get", "way", "see", "make", "like", "know", "take", "come",
    "think", "want", "give", "use", "find", "tell", "ask", "work", "seem", "feel",
    "try", "leave", "call", "keep", "start", "show", "hear", "play", "run", "move",
    "live", "believe", "hold", "bring", "happen", "write", "provide", "sit", "stand", "lose",
    "pay", "meet", "include", "continue", "set", "learn", "change", "lead", "understand", "watch",
    "follow", "stop", "create", "speak", "read", "allow", "add", "spend", "grow", "open",
    "walk", "win", "teach", "offer", "remember", "love", "consider", "appear", "buy", "wait",
    "serve", "die", "send", "expect", "build", "stay", "fall", "cut", "reach", "kill",
    "remain", "suggest", "raise", "pass", "sell", "require", "report", "decide", "pull", "article",
])


class ContentClusterer:
    def __init__(self, model_dir: str = "./data/models/clusters"):
        self.model_dir = model_dir
        self._sklearn_available = self._check_sklearn()
        self._hdbscan_available = self._check_hdbscan()
        self._sentence_tf_available = self._check_sentence_transformers()
        self._kmeans_model = None
        self._cluster_centers = None
        self._cluster_labels = None
        self._cluster_names = {}
        self._embeddings = None
        self._items = []
        self._feature_matrix = None
        self._vectorizer = None

    def _check_sklearn(self) -> bool:
        try:
            from sklearn.cluster import KMeans, AgglomerativeClustering
            return True
        except ImportError:
            return False

    def _check_hdbscan(self) -> bool:
        try:
            import hdbscan
            return True
        except ImportError:
            return False

    def _check_sentence_transformers(self) -> bool:
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            return False

    def _get_embeddings(self, items: list[ContentItem]) -> list[list[float]]:
        if self._sentence_tf_available:
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                texts = [f"{item.title} {item.content[:2000]}" for item in items]
                texts = [t if t.strip() else "empty" for t in texts]
                return model.encode(texts, show_progress_bar=False).tolist()
            except Exception:
                pass
        return self._tfidf_embeddings(items)

    def _tfidf_embeddings(self, items: list[ContentItem]) -> list[list[float]]:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            texts = [self._preprocess(item.content or item.title) for item in items]
            self._vectorizer = TfidfVectorizer(max_features=2000, stop_words='english')
            return self._vectorizer.fit_transform(texts).toarray().tolist()
        except ImportError:
            return self._bow_embeddings(items)

    def _bow_embeddings(self, items: list[ContentItem]) -> list[list[float]]:
        all_texts = []
        for item in items:
            words = self._preprocess(item.content or item.title).split()
            if not words:
                words = ["unknown"]
            all_texts.append(words)
        all_words = set(w for text in all_texts for w in text)
        word_list = sorted(all_words)
        word_index = {w: i for i, w in enumerate(word_list)}

        embeddings = []
        for words in all_texts:
            vec = [0.0] * len(word_list)
            if len(words) > 0:
                for w in words:
                    vec[word_index[w]] += 1.0
                norm = math.sqrt(sum(v * v for v in vec))
                if norm > 0:
                    vec = [v / norm for v in vec]
            embeddings.append(vec)
        return embeddings

    def _preprocess(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'[' + re.escape(string.punctuation) + ']', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
        return ' '.join(words)

    def _find_optimal_k(self, embeddings: list[list[float]], max_k: int = 20) -> int:
        if not self._sklearn_available or len(embeddings) < 4:
            return min(5, max(2, len(embeddings) // 5))
        try:
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
            best_k = 2
            best_score = -1
            max_possible = min(max_k, len(embeddings) - 1)
            for k in range(2, max_possible + 1):
                km = KMeans(n_clusters=k, random_state=42, n_init='auto')
                labels = km.fit_predict(embeddings)
                if len(set(labels)) < 2:
                    continue
                score = silhouette_score(embeddings, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
            return best_k
        except Exception:
            return min(5, max(2, len(embeddings) // 5))

    def _get_top_terms(self, cluster_id: int, n: int = 10) -> list[str]:
        if self._vectorizer is not None and hasattr(self._vectorizer, 'get_feature_names_out'):
            feature_names = self._vectorizer.get_feature_names_out()
            cluster_indices = [i for i, l in enumerate(self._cluster_labels) if l == cluster_id]
            if not cluster_indices or self._feature_matrix is None:
                return []
            cluster_vectors = self._feature_matrix[cluster_indices]
            if hasattr(cluster_vectors, 'toarray'):
                cluster_vectors = cluster_vectors.toarray()
            centroid = cluster_vectors.mean(axis=0)
            top_indices = centroid.argsort()[-n:][::-1]
            return [feature_names[i] for i in top_indices]
        return []

    def _name_cluster(self, cluster_id: int) -> str:
        terms = self._get_top_terms(cluster_id, n=5)
        if terms:
            return ' '.join(terms[:3])
        return f"Cluster_{cluster_id}"

    def cluster(self, items: list[ContentItem], n_clusters: int = None, method: str = "kmeans") -> dict:
        self._items = items
        if len(items) < 2:
            return {
                "clusters": [{"id": 0, "name": "all", "size": len(items), "top_terms": [], "items": [item.id for item in items]}],
                "silhouette_score": 1.0,
                "item_map": {item.id: 0 for item in items},
            }

        embeddings = self._get_embeddings(items)
        n_items = len(embeddings)

        if n_clusters is None:
            n_clusters = self._find_optimal_k(embeddings)
        n_clusters = max(2, min(n_clusters, n_items - 1))

        if method == "kmeans" and self._sklearn_available:
            from sklearn.cluster import KMeans
            self._kmeans_model = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
            self._cluster_labels = self._kmeans_model.fit_predict(embeddings).tolist()
            self._cluster_centers = self._kmeans_model.cluster_centers_
            self._embeddings = embeddings
        elif method == "hdbscan" and self._hdbscan_available:
            import hdbscan
            clusterer = hdbscan.HDBSCAN(min_cluster_size=max(2, n_items // 20), min_samples=1)
            self._cluster_labels = clusterer.fit_predict(embeddings).tolist()
            self._cluster_centers = self._compute_centers(embeddings, self._cluster_labels)
            self._embeddings = embeddings
        elif method == "agglomerative" and self._sklearn_available:
            from sklearn.cluster import AgglomerativeClustering
            agg = AgglomerativeClustering(n_clusters=n_clusters)
            self._cluster_labels = agg.fit_predict(embeddings).tolist()
            self._cluster_centers = self._compute_centers(embeddings, self._cluster_labels)
            self._embeddings = embeddings
        else:
            self._cluster_labels = self._cosine_similarity_grouping(embeddings, n_clusters)
            self._cluster_centers = self._compute_centers(embeddings, self._cluster_labels)
            self._embeddings = embeddings

        unique_clusters = sorted(set(self._cluster_labels))
        item_map = {items[i].id: self._cluster_labels[i] for i in range(n_items)}

        clusters = []
        for cid in unique_clusters:
            if cid < 0:
                continue
            cluster_items = [items[i] for i in range(n_items) if self._cluster_labels[i] == cid]
            top_terms = self._get_top_terms(cid, n=10)
            name = self._name_cluster(cid)
            self._cluster_names[cid] = name
            clusters.append({
                "id": int(cid),
                "name": name,
                "size": len(cluster_items),
                "top_terms": top_terms,
                "items": [item.id for item in cluster_items],
            })

        silhouette = self._compute_silhouette(embeddings, self._cluster_labels)

        return {
            "clusters": clusters,
            "silhouette_score": silhouette,
            "item_map": item_map,
        }

    def _compute_centers(self, embeddings: list[list[float]], labels: list[int]) -> dict:
        centers = {}
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            if label >= 0:
                clusters[label].append(embeddings[i])
        for cid, vecs in clusters.items():
            if vecs:
                centers[cid] = [sum(v[i] for v in vecs) / len(vecs) for i in range(len(vecs[0]))]
        return centers

    def _cosine_similarity_grouping(self, embeddings: list[list[float]], n_clusters: int) -> list[int]:
        n = len(embeddings)
        if n == 0:
            return []
        norms = [math.sqrt(sum(v * v for v in vec)) for vec in embeddings]
        normalized = []
        for vec, norm in zip(embeddings, norms):
            if norm > 0:
                normalized.append([v / norm for v in vec])
            else:
                normalized.append(vec)

        centroids = [normalized[0]]
        for _ in range(1, n_clusters):
            dists = [min(self._cosine_dist(v, c) for c in centroids) for v in normalized]
            centroids.append(normalized[dists.index(max(dists))])

        labels = []
        for vec in normalized:
            dists = [self._cosine_dist(vec, c) for c in centroids]
            labels.append(dists.index(min(dists)))
        return labels

    def _cosine_dist(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        return 1.0 - max(-1.0, min(1.0, dot))

    def _compute_silhouette(self, embeddings: list[list[float]], labels: list[int]) -> float:
        try:
            from sklearn.metrics import silhouette_score
            unique = set(labels)
            noise = sum(1 for l in labels if l < 0)
            if len(unique) - (1 if noise > 0 else 0) < 2:
                return 0.0
            valid = [(e, l) for e, l in zip(embeddings, labels) if l >= 0]
            if len(valid) < 2 or len(set(l for _, l in valid)) < 2:
                return 0.0
            valid_emb = [e for e, _ in valid]
            valid_lbl = [l for _, l in valid]
            return float(silhouette_score(valid_emb, valid_lbl))
        except ImportError:
            return self._silhouette_fallback(embeddings, labels)

    def _silhouette_fallback(self, embeddings: list[list[float]], labels: list[int]) -> float:
        unique = set(l for l in labels if l >= 0)
        if len(unique) < 2:
            return 0.0
        n = len(embeddings)
        if n < 2:
            return 0.0
        scores = []
        for i in range(n):
            if labels[i] < 0:
                continue
            same_cluster = [j for j in range(n) if labels[j] == labels[i] and j != i]
            other_clusters = [j for j in range(n) if labels[j] != labels[i] and labels[j] >= 0]
            if not same_cluster or not other_clusters:
                continue
            a = sum(self._cosine_dist(embeddings[i], embeddings[j]) for j in same_cluster) / len(same_cluster)
            b = float('inf')
            for cid in unique:
                if cid == labels[i]:
                    continue
                members = [j for j in range(n) if labels[j] == cid]
                if not members:
                    continue
                dist = sum(self._cosine_dist(embeddings[i], embeddings[j]) for j in members) / len(members)
                b = min(b, dist)
            if a < b:
                scores.append(1 - a / b if b > 0 else 0)
            elif a > b:
                scores.append(b / a - 1 if a > 0 else 0)
            else:
                scores.append(0)
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    def get_cluster_summary(self, cluster_id: int) -> dict:
        cluster_items = [item for item in self._items if self._cluster_labels is not None and len(self._cluster_labels) > self._items.index(item) and self._cluster_labels[self._items.index(item)] == cluster_id]
        if not cluster_items:
            return {"size": 0, "top_terms": [], "avg_sentiment": 0, "top_sources": [], "sample_items": []}

        top_terms = self._get_top_terms(cluster_id, n=10)
        sentiments = [item.metadata.get("sentiment", {}).get("score", 0) for item in cluster_items if isinstance(item.metadata.get("sentiment"), dict)]
        avg_sent = round(sum(sentiments) / max(len(sentiments), 1), 4) if sentiments else 0
        source_counts = Counter(item.source for item in cluster_items)
        top_sources = [{"source": s, "count": c} for s, c in source_counts.most_common(5)]
        samples = [
            {"id": item.id, "title": item.title[:100], "source": item.source}
            for item in cluster_items[:5]
        ]

        return {
            "size": len(cluster_items),
            "top_terms": top_terms,
            "avg_sentiment": avg_sent,
            "top_sources": top_sources,
            "sample_items": samples,
        }

    def get_cluster_hierarchy(self) -> list[dict]:
        if not self._sklearn_available or len(self._items) < 2:
            return [{"id": 0, "name": "root", "children": []}]
        try:
            from scipy.cluster.hierarchy import linkage, to_tree
            from scipy.spatial.distance import pdist
            embeddings = self._get_embeddings(self._items)
            condensed = pdist(embeddings)
            Z = linkage(condensed, method='ward')
            tree = to_tree(Z)

            def build_tree(node):
                if node is None:
                    return None
                if node.is_leaf():
                    idx = node.get_id()
                    if idx < len(self._items):
                        return {"id": int(idx), "name": self._items[idx].title[:50], "size": 1}
                    return {"id": int(idx), "name": f"leaf_{idx}", "size": 1}
                left = build_tree(node.get_left())
                right = build_tree(node.get_right())
                children = []
                if left:
                    children.append(left)
                if right:
                    children.append(right)
                return {"id": int(node.get_id()), "name": f"cluster_{node.get_id()}", "size": sum(c.get("size", 0) for c in children), "children": children}

            root = build_tree(tree)
            return [root] if root else []
        except Exception:
            return [{"id": 0, "name": "root", "children": []}]

    def assign_to_cluster(self, item: ContentItem) -> int:
        if self._cluster_centers is None or not self._cluster_centers:
            return -1
        emb = self._get_embeddings([item])
        if not emb:
            return -1
        vec = emb[0]
        best_cid = -1
        best_dist = float('inf')
        for cid, center in self._cluster_centers.items():
            dist = self._cosine_dist(vec, center)
            if dist < best_dist:
                best_dist = dist
                best_cid = cid
        return int(best_cid)

    def get_outliers(self, threshold: float = 0.3) -> list[ContentItem]:
        if self._cluster_centers is None or not self._embeddings:
            return []
        outliers = []
        for i, item in enumerate(self._items):
            if i >= len(self._embeddings):
                continue
            vec = self._embeddings[i]
            label = self._cluster_labels[i] if self._cluster_labels and i < len(self._cluster_labels) else -1
            if label < 0:
                outliers.append(item)
                continue
            center = self._cluster_centers.get(label)
            if center is None:
                outliers.append(item)
                continue
            dist = self._cosine_dist(vec, center)
            if dist > threshold:
                outliers.append(item)
        return outliers

    def get_cluster_evolution(self, days: int = 30) -> list[dict]:
        if not self._cluster_labels:
            return []
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=1000)

        since = (datetime.now() - timedelta(days=days)).isoformat()
        cluster_daily = defaultdict(lambda: defaultdict(int))

        for r in results:
            published = r.get("published_at", "")
            if not published or published < since[:10]:
                continue
            date_key = published[:10]
            item_id = r.get("id", "")
            if item_id in self._item_ids():
                idx = self._item_ids().index(item_id)
                if idx < len(self._cluster_labels):
                    cid = self._cluster_labels[idx]
                    if cid >= 0:
                        cluster_daily[date_key][cid] += 1

        evolution = []
        for date_key in sorted(cluster_daily.keys()):
            day_data = {"date": date_key}
            total = sum(cluster_daily[date_key].values())
            for cid in sorted(cluster_daily[date_key].keys()):
                name = self._cluster_names.get(cid, f"Cluster_{cid}")
                day_data[name] = cluster_daily[date_key][cid]
                day_data[f"{name}_pct"] = round(cluster_daily[date_key][cid] / max(total, 1) * 100, 1)
            evolution.append(day_data)
        return evolution

    def _item_ids(self) -> list[str]:
        return [item.id for item in self._items]

    def export_clusters(self, format: str = "json") -> str:
        if not self._cluster_labels:
            return "[]" if format == "json" else "id,cluster"
        if format == "json":
            result = []
            for i, item in enumerate(self._items):
                cid = self._cluster_labels[i] if i < len(self._cluster_labels) else -1
                result.append({"item_id": item.id, "cluster_id": int(cid), "cluster_name": self._cluster_names.get(cid, f"Cluster_{cid}")})
            return json.dumps(result, indent=2)
        lines = ["item_id,cluster_id,cluster_name"]
        for i, item in enumerate(self._items):
            cid = self._cluster_labels[i] if i < len(self._cluster_labels) else -1
            name = self._cluster_names.get(cid, f"Cluster_{cid}")
            lines.append(f"{item.id},{cid},{name}")
        return '\n'.join(lines)
