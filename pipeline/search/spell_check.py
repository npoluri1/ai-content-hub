"""Search spelling correction and 'Did you mean?' using Norvig's algorithm."""

import os
import re
import math
from collections import Counter, defaultdict


class SpellChecker:
    def __init__(self, dictionary_path: str = None):
        self.dictionary_path = dictionary_path or "./data/spell_dict.json"
        self._dictionary = Counter()
        self._technical_terms = set()
        self._total_words = 0
        self._ngram_index = defaultdict(set)
        self._load_dictionary()

    def correct(self, query: str) -> dict:
        if not query.strip():
            return {"original": query, "corrected": query, "has_correction": False, "corrections": [], "did_you_mean": query}

        words = query.split()
        corrections = []
        all_corrected = []

        for word in words:
            word_clean = word.strip("""'\".,!?;:()[]{}""")
            if not word_clean:
                all_corrected.append(word)
                continue

            if word_clean in self._dictionary or word_clean in self._technical_terms:
                all_corrected.append(word)
                continue

            candidates = self._candidates(word_clean)
            if candidates:
                best = candidates[0]
                if best != word_clean:
                    prob = self._probability(best)
                    confidence = min(prob * 100, 0.99)
                    corrections.append({
                        "original": word_clean,
                        "corrected": best,
                        "confidence": round(confidence, 4),
                    })
                    punct = ""
                    if word[-1] in ".,!?;:":
                        punct = word[-1]
                        word = word[:-1]
                    replacement = best + punct
                    all_corrected.append(replacement)
                    continue
            all_corrected.append(word)

        corrected = " ".join(all_corrected)
        has_correction = len(corrections) > 0

        return {
            "original": query,
            "corrected": corrected,
            "has_correction": has_correction,
            "corrections": corrections,
            "did_you_mean": corrected if has_correction and corrected != query else "",
        }

    def suggest(self, query: str, limit: int = 5) -> list[str]:
        if not query.strip():
            return []
        words = query.split()
        suggestions = []
        for word in words[:3]:
            word_clean = word.strip("""'\".,!?;:()[]{}""")
            if word_clean in self._dictionary or word_clean in self._technical_terms:
                continue
            candidates = self._candidates(word_clean)
            suggestions.extend(candidates[:limit])
        return list(dict.fromkeys(suggestions))[:limit]

    def train_from_corpus(self, items: list) -> int:
        words = Counter()
        for item in items:
            text = f"{item.get('title', '')} {item.get('content', '')} {item.get('content_cleaned', '')}"
            tokens = re.findall(r"[a-zA-Z]+", text.lower())
            for t in tokens:
                if len(t) >= 2:
                    words[t] += 1
        self._dictionary.update(words)
        self._total_words = sum(self._dictionary.values())
        self._build_ngram_from_words(words)
        self._save_dictionary()
        return len(words)

    def add_to_dictionary(self, word: str) -> bool:
        word = word.lower().strip()
        if not word or len(word) < 2:
            return False
        self._dictionary[word] += 1
        self._total_words += 1
        self._technical_terms.add(word)
        for n in range(1, 5):
            for i in range(len(word) - n + 1):
                self._ngram_index[word[i:i+n]].add(word)
        self._save_dictionary()
        return True

    def add_technical_terms(self) -> int:
        terms = [
            "langgraph", "chromadb", "mcp", "pytorch", "jax", "cuda", "tensorflow", "keras",
            "scikit", "numpy", "pandas", "huggingface", "transformers", "tokenizers",
            "langchain", "llamaindex", "llama", "mistral", "mixtral", "gemma",
            "openai", "claude", "anthropic", "perplexity", "cohere", "ai21",
            "vectordb", "pinecone", "weaviate", "qdrant", "milvus", "elasticsearch",
            "redis", "postgres", "sqlite", "duckdb", "mongodb", "cassandra",
            "fastapi", "flask", "django", "streamlit", "gradio", "chainlit",
            "docker", "kubernetes", "k8s", "terraform", "ansible", "helm",
            "gcp", "azure", "aws", "bedrock", "sagemaker", "vertex", "lambda",
            "s3", "ec2", "ecs", "eks", "rds", "dynamodb", "cloudfront",
            "mlflow", "wandb", "weights", "biases", "dvc", "kubeflow",
            "ray", "dask", "spark", "flink", "kafka", "rabbitmq", "solace",
            "grpc", "rest", "graphql", "websocket", "sse", "webhook",
            "oauth", "jwt", "saml", "oidc", "mfa", "sso", "ldap",
            "pydantic", "pydanticai", "instructor", "outlines", "guidance",
            "llamafile", "ollama", "vllm", "tgi", "textgen", "exllama",
            "gguf", "ggml", "awq", "gptq", "bitsandbytes", "qlora",
            "peft", "lora", "adapter", "rlhf", "dpo", "ppo", "grpo",
            "neural", "transformer", "attention", "encoder", "decoder",
            "token", "embedding", "latent", "diffusion", "gan", "vae",
            "langsmith", "langfuse", "phoenix", "arize", "truera",
            "nvidia", "amd", "rocm", "triton", "tensorrt", "onnx",
            "kubernetes", "istio", "envoy", "linkerd", "consul",
            "prometheus", "grafana", "jaeger", "tempo", "loki", "datadog",
            "splunk", "newrelic", "dynatrace", "elastic", "opentelemetry",
            "clickhouse", "redpanda", "pulsar", "nats", "celery",
            "prefect", "airflow", "dagster", "mage", "n8n", "temporal",
            "vllm", "sglang", "tabby", "continue", "copilot", "codeium",
            "cursor", "zed", "vscode", "neovim", "emacs", "helix",
            "meltano", "dbt", "great", "expectations", "soda", "monte",
        ]
        count = 0
        for term in terms:
            if term not in self._dictionary and term not in self._technical_terms:
                self.add_to_dictionary(term)
                count += 1
            elif term in self._technical_terms:
                count += 1
        return count

    def build_ngram_index(self, items: list):
        words = Counter()
        for item in items:
            text = f"{item.get('title', '')} {item.get('content', '')}"
            tokens = re.findall(r"[a-zA-Z]+", text.lower())
            for t in tokens:
                if len(t) >= 2:
                    words[t] += 1
        self._build_ngram_from_words(words)

    def get_dictionary_stats(self) -> dict:
        return {
            "total_words": self._total_words,
            "unique_terms": len(self._dictionary),
            "technical_terms": len(self._technical_terms),
        }

    def _build_ngram_from_words(self, words: Counter):
        for word, _count in words.items():
            for n in range(1, 5):
                for i in range(len(word) - n + 1):
                    self._ngram_index[word[i:i+n]].add(word)

    def _load_dictionary(self):
        try:
            import json
            if os.path.exists(self.dictionary_path):
                with open(self.dictionary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._dictionary = Counter(data.get("words", {}))
                self._technical_terms = set(data.get("technical", []))
                self._total_words = sum(self._dictionary.values())
                self._ngram_index = defaultdict(set)
                for word, _count in self._dictionary.items():
                    for n in range(1, 5):
                        for i in range(len(word) - n + 1):
                            self._ngram_index[word[i:i+n]].add(word)
                for t in self._technical_terms:
                    for n in range(1, 5):
                        for i in range(len(t) - n + 1):
                            self._ngram_index[t[i:i+n]].add(t)
        except Exception:
            self._init_defaults()

    def _init_defaults(self):
        default_words = [
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "this", "that", "these", "those", "it", "its", "they", "them",
            "their", "we", "us", "our", "you", "your", "he", "she", "his",
            "her", "who", "which", "what", "when", "where", "why", "how",
            "search", "query", "result", "filter", "sort", "page", "rank",
            "score", "match", "index", "field", "term", "token", "document",
            "relevance", "similarity", "distance", "vector", "embedding",
            "keyword", "phrase", "facet", "boost", "weight", "threshold",
            "summarize", "summarizer", "classify", "classifier", "extract",
            "crawl", "scrape", "fetch", "parse", "ingest", "process",
            "topic", "source", "author", "title", "content", "url", "link",
            "date", "time", "hour", "day", "week", "month", "year",
            "new", "old", "recent", "latest", "trending", "popular",
            "technology", "science", "data", "analysis", "report",
            "system", "model", "application", "platform", "service",
            "news", "article", "blog", "post", "paper", "video", "image",
            "linkedin", "reddit", "twitter", "github", "medium", "youtube",
            "techcrunch", "arxiv", "hacker", "newsletter", "podcast",
            "python", "javascript", "typescript", "rust", "go", "java",
            "cplusplus", "ruby", "swift", "kotlin", "scala", "rlang",
        ]
        for w in default_words:
            self._dictionary[w] += 10
        self._total_words = sum(self._dictionary.values())
        for word, _count in self._dictionary.items():
            for n in range(1, 5):
                for i in range(len(word) - n + 1):
                    self._ngram_index[word[i:i+n]].add(word)

    def _save_dictionary(self):
        try:
            import json
            os.makedirs(os.path.dirname(self.dictionary_path) if os.path.dirname(self.dictionary_path) else ".", exist_ok=True)
            data = {
                "words": dict(self._dictionary.most_common(50000)),
                "technical": list(self._technical_terms),
            }
            with open(self.dictionary_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                cost = 0 if c1 == c2 else 1
                curr.append(min(
                    curr[j] + 1,
                    prev[j + 1] + 1,
                    prev[j] + cost,
                ))
            prev = curr
        return prev[-1]

    def _candidates(self, word: str) -> list[str]:
        word = word.lower()
        if word in self._dictionary:
            return [word]

        candidates = set()

        ngram_matches = set()
        for n in range(2, 5):
            for i in range(len(word) - n + 1):
                ngram = word[i:i+n]
                ngram_matches.update(self._ngram_index.get(ngram, set()))

        for candidate in ngram_matches:
            dist = self._levenshtein_distance(word, candidate)
            if dist == 1:
                candidates.add(candidate)

        if not candidates:
            for candidate in ngram_matches:
                dist = self._levenshtein_distance(word, candidate)
                if dist <= 2:
                    candidates.add(candidate)

        if not candidates:
            for dict_word in self._dictionary:
                if abs(len(dict_word) - len(word)) <= 2:
                    dist = self._levenshtein_distance(word, dict_word)
                    if dist <= 2:
                        candidates.add(dict_word)

        if not candidates and word in self._technical_terms:
            return [word]

        sorted_candidates = sorted(
            candidates,
            key=lambda w: (-self._probability(w), self._levenshtein_distance(word, w))
        )

        return sorted_candidates[:10]

    def _probability(self, word: str) -> float:
        if self._total_words == 0:
            return 0.0
        word = word.lower()
        count = self._dictionary.get(word, 0)
        base_prob = count / self._total_words
        if word in self._technical_terms:
            base_prob = max(base_prob, 0.01)
        return base_prob
