"""Automatic topic discovery using LDA with sklearn fallback to NMF."""

from ..core.models import ContentItem
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from math import log, exp
import json
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
    "also", "around", "back", "become", "below", "between", "came", "come", "day", "does",
    "doing", "done", "down", "each", "end", "far", "few", "get", "go", "going",
    "got", "group", "here", "high", "however", "long", "looking", "made", "make", "might",
    "much", "must", "never", "next", "non", "off", "often", "old", "once", "own",
    "part", "per", "put", "right", "said", "say", "says", "see", "she", "should",
    "show", "side", "since", "small", "still", "take", "tell", "thing", "things", "think",
    "three", "through", "too", "under", "upon", "us", "very", "want", "way", "well",
    "went", "what", "when", "where", "while", "why", "within", "year", "years", "yet",
    "being", "best", "better", "both", "came", "done", "during", "early", "everyone", "few",
    "get", "getting", "give", "given", "gives", "goes", "going", "got", "group", "groups",
    "having", "keep", "keeps", "kept", "kind", "kinds", "know", "known", "knows", "large",
    "largely", "last", "later", "latter", "least", "less", "let", "lets", "like", "likely",
    "long", "longer", "longest", "made", "make", "maker", "makers", "makes", "making", "man",
    "many", "may", "maybe", "me", "mean", "means", "meant", "men", "might", "more",
    "moreover", "most", "mostly", "mr", "mrs", "much", "must", "my", "myself", "name",
    "namely", "near", "nearly", "necessary", "need", "needs", "neither", "never", "nevertheless",
    "new", "next", "no", "nobody", "non", "none", "noone", "nor", "normally", "not",
    "nothing", "now", "nowhere", "obtain", "obtained", "obviously", "of", "off", "often", "oh",
    "ok", "okay", "old", "on", "once", "one", "ones", "only", "onto", "or",
    "other", "others", "ought", "our", "ours", "ourselves", "out", "outside", "over", "overall",
    "own", "paper", "papers", "particular", "particularly", "partly", "past", "per", "perhaps",
    "place", "places", "please", "plus", "point", "points", "possible", "possibly", "present",
    "presents", "presumably", "previously", "primarily", "probably", "problem", "problems", "provided",
    "provides", "purpose", "purposes", "put", "puts", "quite", "rather", "readily", "really",
    "reason", "reasons", "recent", "recently", "regarding", "regardless", "regards", "related",
    "relatively", "research", "respectively", "result", "results", "right", "run", "running",
    "runs", "said", "same", "say", "saying", "says", "second", "seconds", "section",
    "see", "seeing", "seem", "seemed", "seeming", "seems", "seen", "self", "selves",
    "sense", "serious", "seriously", "several", "shall", "she", "should", "show", "showed",
    "shown", "shows", "side", "significant", "significantly", "similar", "similarly", "since",
    "slightly", "small", "smaller", "smallest", "so", "some", "somebody", "somehow", "someone",
    "something", "somewhat", "still", "stop", "stopped", "stopping", "stops", "strong", "strongly",
    "study", "studies", "subsequent", "subsequently", "such", "sufficient", "sufficiently", "suggest",
    "suggested", "suggesting", "suggests", "sure", "surely", "take", "taken", "taking", "tell",
    "tends", "thing", "things", "think", "thinks", "this", "those", "though", "thought",
    "thoughts", "three", "through", "throughout", "thus", "time", "times", "together", "too",
    "took", "toward", "towards", "try", "tried", "tries", "truly", "try", "trying",
    "turn", "turned", "turning", "turns", "type", "types", "under", "undergo", "undergoes",
    "undergone", "underlying", "understand", "understanding", "undertake", "undertaken", "undertakes",
    "underwent", "unfortunately", "unless", "unlike", "unlikely", "until", "unto", "up", "upon",
    "uppon", "upwards", "us", "use", "used", "useful", "usefully", "usefulness", "uses",
    "using", "usually", "various", "very", "via", "view", "viewed", "viewing", "views",
    "vol", "vols", "vs", "want", "wanted", "wanting", "wants", "was", "way", "ways",
    "we", "well", "well", "went", "were", "what", "whatever", "when", "whence", "whenever",
    "where", "whereafter", "whereas", "whereby", "wherein", "whereupon", "wherever", "whether",
    "which", "while", "whim", "whither", "who", "whoever", "whole", "whom", "whose", "why",
    "widely", "widespread", "will", "willing", "willingly", "willingness", "wish", "with",
    "within", "without", "wonder", "wonders", "work", "worked", "working", "works", "would",
    "wouldnt", "yes", "yet", "you", "your", "yours", "yourself", "yourselves",
])


class TopicModeler:
    def __init__(self, model_dir: str = "./data/models/topics"):
        self.model_dir = model_dir
        self._lda_available = self._check_lda()
        self._nmf_available = self._check_nmf()
        self._vectorizer = None
        self._model = None
        self._feature_names = []
        self._doc_topic_dist = None
        self._item_topic_cache = {}

    def _check_lda(self) -> bool:
        try:
            from sklearn.decomposition import LatentDirichletAllocation
            return True
        except ImportError:
            return False

    def _check_nmf(self) -> bool:
        try:
            from sklearn.decomposition import NMF
            return True
        except ImportError:
            return False

    def _preprocess(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'[' + re.escape(string.punctuation) + ']', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split()
        words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        return ' '.join(words)

    def _stem_words(self, words: list[str]) -> list[str]:
        try:
            from nltk.stem import PorterStemmer
            stemmer = PorterStemmer()
            return [stemmer.stem(w) for w in words]
        except ImportError:
            try:
                import re as re_mod
                suffixes = ['ing', 'ed', 'ly', 'es', 's', 'ment', 'tion', 'ness', 'able', 'ible']
                result = []
                for w in words:
                    for s in suffixes:
                        if w.endswith(s) and len(w) > len(s) + 2:
                            w = w[:-len(s)]
                            break
                    result.append(w)
                return result
            except Exception:
                return words

    def discover_topics(self, items: list[ContentItem], n_topics: int = 10, n_top_words: int = 20) -> dict:
        corpus = [self._preprocess(item.content or item.title) for item in items]
        if not any(c for c in corpus):
            return {"topics": [], "coherence_score": 0, "item_topic_map": {}}

        result = self.train_lda(corpus, n_topics=n_topics, passes=10)
        if not result.get("labels"):
            return {"topics": [], "coherence_score": 0, "item_topic_map": {}}

        topics = []
        for topic_id, words in result["topic_words"].items():
            topics.append({
                "id": topic_id,
                "name": ' '.join(words[:5]),
                "words": words,
                "weight": float(result.get("topic_weights", {}).get(topic_id, 1.0)),
            })

        labels = result["labels"]
        item_topic_map = {}
        for i, item in enumerate(items):
            if i < len(labels):
                item_topic_map[item.id] = {"topic_id": int(labels[i]), "weight": 1.0}

        return {
            "topics": topics,
            "coherence_score": result.get("coherence_score", 0),
            "item_topic_map": item_topic_map,
        }

    def train_lda(self, corpus: list[str], n_topics: int = 10, passes: int = 10) -> dict:
        from sklearn.feature_extraction.text import CountVectorizer

        preprocessed = [self._preprocess(doc) for doc in corpus]
        non_empty = [d for d in preprocessed if d.strip()]
        if len(non_empty) < 2:
            return {"labels": [0]*len(corpus), "topic_words": {0: ["no_content"]}, "coherence_score": 0, "topic_weights": {0: 1.0}}

        self._vectorizer = CountVectorizer(max_df=0.85, min_df=2, max_features=5000, stop_words='english')
        dtm = self._vectorizer.fit_transform(non_empty)
        self._feature_names = self._vectorizer.get_feature_names_out()

        if n_topics > len(non_empty):
            n_topics = max(2, len(non_empty) // 2)

        if self._lda_available:
            from sklearn.decomposition import LatentDirichletAllocation
            self._model = LatentDirichletAllocation(
                n_components=n_topics, max_iter=50, learning_method='online',
                learning_offset=50., random_state=42, n_jobs=-1
            )
            self._doc_topic_dist = self._model.fit_transform(dtm)
            topic_word_dist = self._model.components_
        elif self._nmf_available:
            from sklearn.decomposition import NMF
            self._model = NMF(n_components=n_topics, random_state=42, max_iter=500)
            self._doc_topic_dist = self._model.fit_transform(dtm)
            topic_word_dist = self._model.components_
        else:
            return self._simple_keyword_grouping(non_empty, n_topics)

        topic_words = {}
        topic_weights = {}
        for topic_idx, topic in enumerate(topic_word_dist):
            top_indices = topic.argsort()[:-n_topics - 1:-1]
            words = [self._feature_names[i] for i in top_indices]
            stemmed = self._stem_words(words)
            topic_words[int(topic_idx)] = stemmed[:20]
            topic_weights[int(topic_idx)] = float(topic.sum())

        labels = self._doc_topic_dist.argmax(axis=1).tolist()
        coherence = self._compute_coherence(topic_words, non_empty)

        result = {
            "labels": labels,
            "topic_words": topic_words,
            "coherence_score": coherence,
            "topic_weights": topic_weights,
            "doc_topic_dist": self._doc_topic_dist.tolist(),
        }
        self._item_topic_cache.clear()
        return result

    def _compute_coherence(self, topic_words: dict, corpus: list[str]) -> float:
        doc_word_sets = [set(doc.split()) for doc in corpus if doc.strip()]
        if not doc_word_sets:
            return 0.0

        scores = []
        for tid, words in topic_words.items():
            top_n = words[:10]
            if len(top_n) < 2:
                continue
            pair_scores = []
            for i in range(len(top_n)):
                for j in range(i + 1, len(top_n)):
                    w1, w2 = top_n[i], top_n[j]
                    w1_count = sum(1 for ds in doc_word_sets if w1 in ds)
                    w2_count = sum(1 for ds in doc_word_sets if w2 in ds)
                    both_count = sum(1 for ds in doc_word_sets if w1 in ds and w2 in ds)
                    if w1_count > 0 and w2_count > 0:
                        pair_scores.append(both_count / (w1_count * w2_count) * len(doc_word_sets))
            if pair_scores:
                scores.append(sum(pair_scores) / len(pair_scores))

        return round(sum(scores) / max(len(scores), 1), 4) if scores else 0.0

    def _simple_keyword_grouping(self, corpus: list[str], n_topics: int) -> dict:
        doc_words = [doc.split() for doc in corpus]
        all_words = [w for doc in doc_words for w in doc]
        word_freq = Counter(all_words)
        top_words = [w for w, _ in word_freq.most_common(100)]
        chunk_size = max(1, len(top_words) // max(n_topics, 1))

        topic_words = {}
        for i in range(n_topics):
            start = i * chunk_size
            end = start + chunk_size if i < n_topics - 1 else len(top_words)
            topic_words[i] = top_words[start:end] if end > start else ["misc"]

        labels = []
        for doc in doc_words:
            best_topic = 0
            best_score = -1
            for tid, twords in topic_words.items():
                score = sum(1 for w in doc if w in twords)
                if score > best_score:
                    best_score = score
                    best_topic = tid
            labels.append(best_topic)

        topic_weights = {}
        for tid, twords in topic_words.items():
            topic_weights[tid] = len(twords)

        return {
            "labels": labels,
            "topic_words": topic_words,
            "coherence_score": 0.0,
            "topic_weights": topic_weights,
            "doc_topic_dist": [],
        }

    def predict_topic(self, text: str) -> dict:
        if self._model is None or self._vectorizer is None:
            return {}

        preprocessed = self._preprocess(text)
        if not preprocessed.strip():
            return {}

        vec = self._vectorizer.transform([preprocessed])
        if self._lda_available:
            dist = self._model.transform(vec)[0]
        elif self._nmf_available:
            dist = self._model.transform(vec)[0]
        else:
            return {}

        result = {}
        for i, prob in enumerate(dist):
            result[int(i)] = round(float(prob), 6)
        return result

    def get_topic_words(self, topic_id: int, n: int = 20) -> list[str]:
        if self._model is None:
            return []
        if hasattr(self._model, 'components_'):
            if topic_id >= self._model.components_.shape[0]:
                return []
            topic = self._model.components_[topic_id]
            top_indices = topic.argsort()[:-n - 1:-1]
            return [self._feature_names[i] for i in top_indices]
        return []

    def get_item_topic(self, item: ContentItem) -> dict:
        if item.id in self._item_topic_cache:
            return self._item_topic_cache[item.id]
        result = self.predict_topic(item.content or item.title)
        self._item_topic_cache[item.id] = result
        return result

    def get_topic_trend(self, topic_id: int, days: int = 30) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=1000)

        since = (datetime.now() - timedelta(days=days)).isoformat()
        daily_counts = defaultdict(int)
        daily_total = defaultdict(int)

        for r in results:
            published = r.get("published_at", "")
            if not published or published < since[:10]:
                continue
            text = f"{r.get('title', '')} {r.get('content', '')}"
            if not text.strip():
                continue
            date_key = published[:10]
            pred = self.predict_topic(text)
            if pred:
                top_topic = max(pred, key=pred.get)
                if top_topic == topic_id:
                    daily_counts[date_key] += 1
            daily_total[date_key] += 1

        trend = []
        for date_key in sorted(daily_counts.keys()):
            total = daily_total.get(date_key, 1)
            trend.append({
                "date": date_key,
                "count": daily_counts[date_key],
                "proportion": round(daily_counts[date_key] / max(total, 1), 4),
            })
        return trend

    def compare_topics(self, topic_id_a: int, topic_id_b: int) -> float:
        if self._model is None or not hasattr(self._model, 'components_'):
            return 0.0
        n_components = self._model.components_.shape[0]
        if topic_id_a >= n_components or topic_id_b >= n_components:
            return 0.0

        p = self._model.components_[topic_id_a].astype(float)
        q = self._model.components_[topic_id_b].astype(float)
        p = p / p.sum()
        q = q / q.sum()
        m = 0.5 * (p + q)
        kl_pm = sum(p[i] * log(p[i] / m[i]) for i in range(len(p)) if p[i] > 0 and m[i] > 0)
        kl_qm = sum(q[i] * log(q[i] / m[i]) for i in range(len(q)) if q[i] > 0 and m[i] > 0)
        js = 0.5 * (kl_pm + kl_qm)
        return round(float(js), 6)

    def merge_similar_topics(self, threshold: float = 0.8) -> dict:
        if self._model is None or not hasattr(self._model, 'components_'):
            return {"merged": [], "remaining": []}

        n_topics = self._model.components_.shape[0]
        similarities = {}
        to_merge = set()
        merge_map = {}

        for i in range(n_topics):
            for j in range(i + 1, n_topics):
                sim = self.compare_topics(i, j)
                similarities[(i, j)] = sim
                if sim < threshold:
                    continue
                to_merge.add(j)
                if i not in merge_map:
                    merge_map[i] = []
                merge_map[i].append(j)

        remaining = [i for i in range(n_topics) if i not in to_merge]
        merged_ids = list(to_merge)

        return {
            "merged": [{"kept": k, "absorbed": v} for k, v in merge_map.items()],
            "remaining": remaining,
            "n_merged": len(merged_ids),
            "n_remaining": len(remaining),
        }

    def visualize_topics(self, method: str = "pyldavis") -> str:
        try:
            import pyLDAvis
            import pyLDAvis.sklearn
            if self._model is not None and self._vectorizer is not None and hasattr(self._model, 'components_'):
                from sklearn.feature_extraction.text import CountVectorizer
                prepared = pyLDAvis.sklearn.prepare(self._model, None, self._vectorizer)
                out_path = os.path.join(self.model_dir, "pyldavis.html")
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                pyLDAvis.save_html(prepared, out_path)
                return out_path
        except ImportError:
            pass

        result_lines = [f"Topic Visualization (pyLDAvis not available, n_topics={self._model.components_.shape[0] if self._model is not None and hasattr(self._model, 'components_') else 'N/A'})"]
        if self._model is not None and hasattr(self._model, 'components_'):
            for tid in range(self._model.components_.shape[0]):
                words = self.get_topic_words(tid, n=10)
                result_lines.append(f"Topic {tid}: {', '.join(words)}")
        return '\n'.join(result_lines)

    def save_model(self, path: str = None) -> bool:
        save_path = path or os.path.join(self.model_dir, "topic_model.pkl")
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                pickle.dump({
                    'model': self._model,
                    'vectorizer': self._vectorizer,
                    'feature_names': self._feature_names,
                    'doc_topic_dist': self._doc_topic_dist,
                }, f)
            return True
        except Exception:
            return False

    def load_model(self, path: str = None) -> bool:
        load_path = path or os.path.join(self.model_dir, "topic_model.pkl")
        try:
            with open(load_path, 'rb') as f:
                data = pickle.load(f)
            self._model = data.get('model')
            self._vectorizer = data.get('vectorizer')
            self._feature_names = data.get('feature_names', [])
            self._doc_topic_dist = data.get('doc_topic_dist')
            return True
        except Exception:
            return False
