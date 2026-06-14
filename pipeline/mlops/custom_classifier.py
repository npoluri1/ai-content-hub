"""Train and use custom content classifiers with sklearn and fallback methods."""

from ..core.models import ContentItem
from collections import defaultdict, Counter
import json
import math
import os
import pickle
import re
import sqlite3
import string
import uuid


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

BUILTIN_CLASSIFIERS = {
    "content_type": {
        "description": "Classify content by type: tutorial, news, opinion, research, discussion, announcement, review",
        "labels": ["tutorial", "news", "opinion", "research", "discussion", "announcement", "review"],
        "examples": {
            "tutorial": [
                "how to build a RAG pipeline step by step",
                "getting started with LangGraph tutorial",
                "guide to fine-tuning LLMs with LoRA",
                "walkthrough of deploying ML models to production",
                "hands-on example of building a chatbot",
                "step by step guide to implementing MCP servers",
            ],
            "news": [
                "OpenAI announces GPT-5 with groundbreaking capabilities",
                "Microsoft and Anthropic partner on new AI safety initiative",
                "Google releases Gemini 2.0 with native tool use",
                "Meta launches Llama 4 as open source model",
                "NVIDIA reports record revenue from AI chip sales",
            ],
            "opinion": [
                "why I think AGI is closer than we think",
                "my take on the future of AI regulation",
                "the case against open sourcing powerful models",
                "IMO the transformer architecture is near its limit",
                "why we should be optimistic about AI safety",
            ],
            "research": [
                "we propose a novel attention mechanism for long context",
                "empirical evaluation of chain-of-thought prompting",
                "a comprehensive survey of MCP protocols",
                "state-of-the-art results on GSM8K with new approach",
                "novel architecture for efficient video generation",
            ],
            "discussion": [
                "what are your thoughts on the new AI regulations",
                "poll: do you use LangChain or build from scratch",
                "advice needed: best vector database for production",
                "anyone else experiencing issues with GPT-4o API",
                "tell me your favorite AI productivity tools",
            ],
            "announcement": [
                "announcing our new open source LLM evaluation framework",
                "we're excited to launch version 2.0 of our platform",
                "introducing real-time streaming for all API endpoints",
                "now available: fine-tuning for custom models",
                "shipping our first production release of the AI agent",
            ],
            "review": [
                "Claude 4 review: worth the upgrade?",
                "GPT-5 vs Claude 4 vs Gemini 2.5 comparison",
                "hands-on review of Cursor AI IDE",
                "testing the new MCP protocol implementation",
                "LangGraph vs CrewAI: which agent framework wins",
            ],
        },
    },
    "sentiment_tier": {
        "description": "Five-tier sentiment classification",
        "labels": ["very_positive", "positive", "neutral", "negative", "very_negative"],
        "examples": {
            "very_positive": [
                "absolutely groundbreaking breakthrough in AI research",
                "this is the most amazing technology I have ever seen",
                "incredible performance that exceeds all expectations",
                "perfect solution that solves everything flawlessly",
                "phenomenal achievement that changes everything",
            ],
            "positive": [
                "good progress on the new model architecture",
                "impressive results from the latest benchmark",
                "useful improvement to the existing framework",
                "solid performance with better accuracy",
                "helpful update that addresses key issues",
            ],
            "neutral": [
                "the new update changes some of the API endpoints",
                "version 2.0 has been released with minor changes",
                "the paper presents a modified approach to the problem",
                "they announced a partnership for joint development",
                "the company reported quarterly earnings yesterday",
            ],
            "negative": [
                "the model fails to handle basic edge cases",
                "disappointing performance compared to alternatives",
                "several bugs were reported in the latest release",
                "limited functionality in the free tier",
                "below average results on standard benchmarks",
            ],
            "very_negative": [
                "this is completely broken and unusable",
                "terrible implementation that causes data loss",
                "worst API design I have ever encountered",
                "catastrophic failure in production environment",
                "horrible experience with terrible customer support",
            ],
        },
    },
    "urgency": {
        "description": "Content urgency level",
        "labels": ["critical", "high", "normal", "low"],
        "examples": {
            "critical": [
                "security vulnerability found in production system",
                "critical bug causing data corruption",
                "immediate action required: service outage",
                "urgent security patch needed for all deployments",
                "emergency maintenance scheduled for today",
            ],
            "high": [
                "important update that may affect your workflow",
                "breaking changes in latest release",
                "deprecation notice for key features",
                "urgent: please review the new API changes",
                "significant performance regression detected",
            ],
            "normal": [
                "new feature released in latest version",
                "weekly roundup of AI news and developments",
                "tutorial on using the new API endpoints",
                "community discussion about best practices",
                "comparison of different approaches",
            ],
            "low": [
                "tip of the day: keyboard shortcuts",
                "fun fact about machine learning history",
                "community spotlight: interesting project",
                "upcoming conference and events calendar",
                "thought leadership piece on future trends",
            ],
        },
    },
    "readability": {
        "description": "Content readability level",
        "labels": ["easy", "medium", "hard"],
        "examples": {
            "easy": [
                "AI helps us write better code",
                "you can use GPT to chat with your data",
                "just click the button to start",
                "this tool makes it simple to build apps",
                "anyone can learn machine learning basics",
            ],
            "medium": [
                "the transformer architecture uses attention mechanisms",
                "fine-tuning requires labeled training data",
                "vector databases store embeddings for similarity search",
                "RAG combines retrieval with generation for better answers",
                "agentic workflows chain together multiple LLM calls",
            ],
            "hard": [
                "we demonstrate superior performance through a novel sparse attention mechanism",
                "the empirical results show statistically significant improvement over baselines",
                "our theoretical analysis provides bounds on the approximation error",
                "the computational complexity scales quadratically with sequence length",
                "we propose a multi-task learning framework with auxiliary objectives",
            ],
        },
    },
}


class CustomClassifier:
    def __init__(self, model_dir: str = "./data/models/classifiers"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self._sklearn_available = self._check_sklearn()
        self._db_path = os.path.join(self.model_dir, "classifiers.db")
        self._init_db()
        self._models = {}
        self._vectorizers = {}
        self._classifier_info = {}
        self._load_registered_classifiers()

    def _check_sklearn(self) -> bool:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            return True
        except ImportError:
            return False

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS classifiers (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                labels TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trained_at TIMESTAMP,
                accuracy REAL DEFAULT 0,
                f1_score REAL DEFAULT 0,
                precision REAL DEFAULT 0,
                recall REAL DEFAULT 0,
                confusion_matrix TEXT DEFAULT '{}',
                label_counts TEXT DEFAULT '{}'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS classifier_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classifier_id TEXT NOT NULL,
                text TEXT NOT NULL,
                label TEXT NOT NULL,
                source_item_id TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (classifier_id) REFERENCES classifiers(id)
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_examples_classifier
            ON classifier_examples(classifier_id)
        """)
        conn.commit()
        conn.close()

    def _load_registered_classifiers(self):
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT id, name, labels, description FROM classifiers")
        rows = c.fetchall()
        conn.close()
        for row in rows:
            cid, name, labels_str, desc = row
            self._classifier_info[cid] = {
                "id": cid, "name": name,
                "labels": json.loads(labels_str),
                "description": desc,
            }
            model_path = os.path.join(self.model_dir, f"{cid}_model.pkl")
            vec_path = os.path.join(self.model_dir, f"{cid}_vectorizer.pkl")
            if os.path.exists(model_path) and os.path.exists(vec_path):
                try:
                    with open(model_path, 'rb') as f:
                        self._models[cid] = pickle.load(f)
                    with open(vec_path, 'rb') as f:
                        self._vectorizers[cid] = pickle.load(f)
                except Exception:
                    pass

        for name, config in BUILTIN_CLASSIFIERS.items():
            existing = [v for v in self._classifier_info.values() if v["name"] == name]
            if not existing:
                cid = self._create_classifier_in_db(name, config["labels"], config["description"])
                for label, examples in config["examples"].items():
                    for ex_text in examples:
                        self._add_example_to_db(cid, ex_text, label)

    def _create_classifier_in_db(self, name: str, labels: list[str], description: str) -> str:
        cid = str(uuid.uuid4())[:8]
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO classifiers (id, name, labels, description) VALUES (?, ?, ?, ?)",
            (cid, name, json.dumps(labels), description)
        )
        conn.commit()
        conn.close()
        self._classifier_info[cid] = {"id": cid, "name": name, "labels": labels, "description": description}
        return cid

    def _add_example_to_db(self, classifier_id: str, text: str, label: str, source_item_id: str = ""):
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO classifier_examples (classifier_id, text, label, source_item_id) VALUES (?, ?, ?, ?)",
            (classifier_id, text, label, source_item_id)
        )
        conn.commit()
        conn.close()

    def create_classifier(self, name: str, labels: list[str], description: str = "") -> str:
        existing = [v for v in self._classifier_info.values() if v["name"] == name]
        if existing:
            return existing[0]["id"]
        cid = self._create_classifier_in_db(name, labels, description)
        return cid

    def add_examples(self, classifier_id: str, items: list[ContentItem], label: str) -> int:
        count = 0
        for item in items:
            text = f"{item.title} {item.content}"
            if text.strip():
                self._add_example_to_db(classifier_id, text, label, item.id)
                count += 1
        return count

    def train(self, classifier_id: str) -> dict:
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT text, label FROM classifier_examples WHERE classifier_id = ?", (classifier_id,))
        rows = c.fetchall()
        conn.close()

        if len(rows) < 2:
            labels = self._classifier_info.get(classifier_id, {}).get("labels", [])
            return {"accuracy": 0, "f1_score": 0, "precision": 0, "recall": 0, "confusion_matrix": {}, "label_counts": {l: 0 for l in labels}, "error": "Need at least 2 training examples"}

        texts = []
        labels = []
        for t, l in rows:
            processed = self._preprocess(t)
            if processed.strip():
                texts.append(processed)
                labels.append(l)

        if len(texts) < 2:
            return {"accuracy": 0, "f1_score": 0, "precision": 0, "recall": 0, "confusion_matrix": {}, "label_counts": {}, "error": "Need at least 2 valid training examples"}

        if self._sklearn_available:
            result = self._train_sklearn(classifier_id, texts, labels)
        else:
            result = self._train_centroid(classifier_id, texts, labels)

        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute(
            "UPDATE classifiers SET trained_at = CURRENT_TIMESTAMP, accuracy = ?, f1_score = ?, precision = ?, recall = ?, confusion_matrix = ?, label_counts = ? WHERE id = ?",
            (result["accuracy"], result["f1_score"], result["precision"], result["recall"],
             json.dumps(result["confusion_matrix"]), json.dumps(result["label_counts"]), classifier_id)
        )
        conn.commit()
        conn.close()

        return result

    def _train_sklearn(self, classifier_id: str, texts: list[str], labels: list[str]) -> dict:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

        vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words='english')
        X = vectorizer.fit_transform(texts)

        unique_labels = sorted(set(labels))
        n_classes = len(unique_labels)
        min_samples = min(Counter(labels).values())

        if len(texts) >= 10 and n_classes >= 2 and min_samples >= 2:
            try:
                test_size = max(0.2, 2 / len(texts))
                X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=test_size, random_state=42, stratify=labels if min_samples >= 2 else None)
                model = LogisticRegression(max_iter=1000, random_state=42, multi_class='multinomial' if n_classes > 2 else 'ovr')
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                f1 = f1_score(y_test, y_pred, average='weighted')
                precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
                recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
                cm = confusion_matrix(y_test, y_pred).tolist()
            except Exception:
                model = LogisticRegression(max_iter=1000, random_state=42)
                model.fit(X, labels)
                y_pred = model.predict(X)
                accuracy = accuracy_score(labels, y_pred)
                f1 = f1_score(labels, y_pred, average='weighted')
                precision = precision_score(labels, y_pred, average='weighted', zero_division=0)
                recall = recall_score(labels, y_pred, average='weighted', zero_division=0)
                cm = confusion_matrix(labels, y_pred).tolist()
        else:
            model = LogisticRegression(max_iter=1000, random_state=42)
            model.fit(X, labels)
            y_pred = model.predict(X)
            accuracy = accuracy_score(labels, y_pred)
            f1 = f1_score(labels, y_pred, average='weighted')
            precision = precision_score(labels, y_pred, average='weighted', zero_division=0)
            recall = recall_score(labels, y_pred, average='weighted', zero_division=0)
            cm = confusion_matrix(labels, y_pred).tolist()

        self._models[classifier_id] = model
        self._vectorizers[classifier_id] = vectorizer

        model_path = os.path.join(self.model_dir, f"{classifier_id}_model.pkl")
        vec_path = os.path.join(self.model_dir, f"{classifier_id}_vectorizer.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        with open(vec_path, 'wb') as f:
            pickle.dump(vectorizer, f)

        label_counts = dict(Counter(labels))

        return {"accuracy": round(accuracy, 4), "f1_score": round(f1, 4), "precision": round(precision, 4), "recall": round(recall, 4), "confusion_matrix": cm, "label_counts": label_counts}

    def _train_centroid(self, classifier_id: str, texts: list[str], labels: list[str]) -> dict:
        unique_labels = sorted(set(labels))
        centroids = {}
        all_vectors = []
        all_labels = []

        for label in unique_labels:
            label_texts = [t for t, l in zip(texts, labels) if l == label]
            vectors = [self._text_to_vector(t) for t in label_texts]
            if vectors:
                centroid = [sum(v[i] for v in vectors) / len(vectors) for i in range(len(vectors[0]))]
                centroids[label] = centroid
                all_vectors.extend(vectors)
                all_labels.extend([label] * len(vectors))

        self._models[classifier_id] = centroids

        correct = 0
        for vec, actual in zip(all_vectors, all_labels):
            best_label = None
            best_sim = -float('inf')
            for label, centroid in centroids.items():
                sim = self._cosine_sim(vec, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_label = label
            if best_label == actual:
                correct += 1

        total = len(all_vectors)
        accuracy = correct / max(total, 1)

        label_counts = dict(Counter(labels))

        return {"accuracy": round(accuracy, 4), "f1_score": round(accuracy, 4), "precision": round(accuracy, 4), "recall": round(accuracy, 4), "confusion_matrix": {}, "label_counts": label_counts}

    def _preprocess(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'[' + re.escape(string.punctuation) + ']', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
        return ' '.join(words)

    def _text_to_vector(self, text: str) -> list[float]:
        words = text.split()
        word_set = set(words)
        base_words = ["ai", "model", "build", "use", "new", "data", "system", "learn", "train", "api",
                      "tool", "code", "app", "platform", "feature", "release", "update", "version",
                      "research", "paper", "study", "result", "perform", "improve", "change",
                      "good", "great", "bad", "terrible", "amazing", "worst", "best", "better",
                      "how", "what", "why", "guide", "tutorial", "step", "example",
                      "announce", "launch", "introduce", "partner", "acquire", "invest",
                      "think", "believe", "opinion", "perspective", "view",
                      "review", "compare", "vs", "versus", "alternative", "worth",
                      "help", "advice", "recommend", "suggest", "question", "discuss",
                      "breakthrough", "revolutionary", "groundbreaking", "game", "changing",
                      "fail", "error", "bug", "crash", "issue", "problem", "slow",
                      "security", "vulnerability", "patch", "fix", "emergency", "urgent"]
        vec = []
        for bw in base_words:
            vec.append(1.0 if bw in word_set else 0.0)
        if words:
            vec.append(len(words) / 100.0)
            vec.append(len(set(words)) / max(len(words), 1))
        else:
            vec.extend([0.0, 0.0])
        return vec

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0
        return dot / (na * nb)

    def predict(self, classifier_id: str, text: str) -> dict:
        if classifier_id not in self._models:
            return {"label": "unknown", "confidence": 0, "probabilities": {}}

        processed = self._preprocess(text)

        if classifier_id in self._vectorizers:
            vectorizer = self._vectorizers[classifier_id]
            model = self._models[classifier_id]
            X = vectorizer.transform([processed])
            try:
                probs = model.predict_proba(X)[0]
                pred_idx = model.predict(X)[0]
                label = model.classes_[pred_idx] if hasattr(pred_idx, '__iter__') else pred_idx
                if isinstance(label, (int, float)):
                    label = model.classes_[int(label)]
                probabilities = {str(model.classes_[i]): round(float(probs[i]), 6) for i in range(len(probs))}
                confidence = round(float(max(probs)), 6)
                return {"label": str(label), "confidence": confidence, "probabilities": probabilities}
            except Exception:
                pred = model.predict(X)[0]
                if isinstance(pred, (int, float)):
                    pred = model.classes_[int(pred)]
                return {"label": str(pred), "confidence": 0.5, "probabilities": {str(pred): 0.5}}

        centroids = self._models[classifier_id]
        if isinstance(centroids, dict):
            vec = self._text_to_vector(processed)
            best_label = None
            best_sim = -float('inf')
            for label, centroid in centroids.items():
                sim = self._cosine_sim(vec, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_label = label
            probs = {l: round(float(self._cosine_sim(vec, c)), 6) for l, c in centroids.items()}
            total = sum(probs.values()) if sum(probs.values()) > 0 else 1
            normalized = {l: round(p / total, 6) for l, p in probs.items()}
            return {"label": str(best_label), "confidence": round(float(best_sim), 6), "probabilities": normalized}

        return {"label": "unknown", "confidence": 0, "probabilities": {}}

    def predict_item(self, classifier_id: str, item: ContentItem) -> ContentItem:
        text = f"{item.title} {item.content}"
        result = self.predict(classifier_id, text)
        if "classifications" not in item.metadata:
            item.metadata["classifications"] = {}
        item.metadata["classifications"][classifier_id] = result
        return item

    def predict_batch(self, classifier_id: str, items: list[ContentItem]) -> list[ContentItem]:
        return [self.predict_item(classifier_id, item) for item in items]

    def get_classifier_info(self, classifier_id: str) -> dict:
        info = self._classifier_info.get(classifier_id, {})
        if not info:
            return {"error": "Classifier not found"}
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute(
            "SELECT accuracy, f1_score, precision, recall, confusion_matrix, label_counts, trained_at FROM classifiers WHERE id = ?",
            (classifier_id,)
        )
        row = c.fetchone()
        conn.close()
        if row:
            info["metrics"] = {
                "accuracy": row[0], "f1_score": row[1],
                "precision": row[2], "recall": row[3],
            }
            info["confusion_matrix"] = json.loads(row[4]) if row[4] else {}
            info["label_counts"] = json.loads(row[5]) if row[5] else {}
            info["trained_at"] = row[6]
        return info

    def list_classifiers(self) -> list[dict]:
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT id, name, labels, description, created_at, trained_at FROM classifiers ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        return [
            {
                "id": r[0], "name": r[1],
                "labels": json.loads(r[2]) if isinstance(r[2], str) else r[2],
                "description": r[3], "created_at": r[4], "trained_at": r[5],
            }
            for r in rows
        ]

    def delete_classifier(self, classifier_id: str) -> bool:
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("DELETE FROM classifier_examples WHERE classifier_id = ?", (classifier_id,))
        c.execute("DELETE FROM classifiers WHERE id = ?", (classifier_id,))
        conn.commit()
        conn.close()

        self._models.pop(classifier_id, None)
        self._vectorizers.pop(classifier_id, None)
        self._classifier_info.pop(classifier_id, None)

        for fname in [f"{classifier_id}_model.pkl", f"{classifier_id}_vectorizer.pkl"]:
            fpath = os.path.join(self.model_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
        return True

    def export_training_data(self, classifier_id: str, format: str = "json") -> str:
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT text, label, source_item_id FROM classifier_examples WHERE classifier_id = ?", (classifier_id,))
        rows = c.fetchall()
        conn.close()

        if format == "json":
            data = [{"text": r[0], "label": r[1], "source_item_id": r[2]} for r in rows]
            return json.dumps(data, indent=2)
        lines = ["text,label,source_item_id"]
        for r in rows:
            escaped = r[0].replace('"', '""')
            lines.append(f'"{escaped}",{r[1]},{r[2]}')
        return '\n'.join(lines)

    def import_training_data(self, classifier_id: str, file_path: str) -> int:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        count = 0
        if file_path.endswith('.json'):
            data = json.loads(content)
            for entry in data:
                text = entry.get("text", "")
                label = entry.get("label", "")
                sid = entry.get("source_item_id", "")
                if text and label:
                    self._add_example_to_db(classifier_id, text, label, sid)
                    count += 1
        elif file_path.endswith('.csv'):
            lines = content.strip().split('\n')[1:]
            for line in lines:
                parts = line.split(',', 2)
                if len(parts) >= 2:
                    text = parts[0].strip('"')
                    label = parts[1].strip()
                    sid = parts[2] if len(parts) > 2 else ""
                    if text and label:
                        self._add_example_to_db(classifier_id, text, label, sid)
                        count += 1
        else:
            lines = content.strip().split('\n')
            for line in lines:
                if '\t' in line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        text, label = parts[0].strip(), parts[1].strip()
                        self._add_example_to_db(classifier_id, text, label)
                        count += 1

        return count

    def get_performance(self, classifier_id: str) -> dict:
        info = self.get_classifier_info(classifier_id)
        if "error" in info:
            return info

        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM classifier_examples WHERE classifier_id = ?", (classifier_id,))
        total_examples = c.fetchone()[0]
        c.execute("SELECT label, COUNT(*) FROM classifier_examples WHERE classifier_id = ? GROUP BY label", (classifier_id,))
        label_dist = {r[0]: r[1] for r in c.fetchall()}
        conn.close()

        return {
            "classifier_id": classifier_id,
            "name": info.get("name", ""),
            "labels": info.get("labels", []),
            "total_examples": total_examples,
            "label_distribution": label_dist,
            "metrics": info.get("metrics", {}),
            "is_trained": info.get("trained_at") is not None,
        }
