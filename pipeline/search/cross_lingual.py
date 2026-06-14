"""Cross-lingual search — detect, translate, and search across languages."""

from ..core.models import ContentItem
from ..storage.vector_store import VectorStore
from ..storage.sql_store import SQLStore
import re
import json
import urllib.request
import urllib.parse


class CrossLingualSearch:
    def __init__(self, vector_store=None):
        self.vector = vector_store or VectorStore()
        self.sql = SQLStore()
        self._libre_url = "https://libretranslate.com"
        self._detector = None

    def search(self, query: str, source_language: str = "auto",
               target_languages: list[str] = None, n_results: int = 20) -> list[dict]:
        if source_language == "auto":
            source_language = self.detect_language(query)

        target_languages = target_languages or ["en"]
        all_results = []

        if source_language in target_languages or source_language == "en":
            results = self.vector.search(query, n_results=n_results)
            for r in results:
                parsed = self._parse_result(r)
                parsed["_language"] = source_language
                all_results.append(parsed)

        for lang in target_languages:
            if lang == source_language:
                continue
            translated = self.translate_query(query, lang)
            results = self.vector.search(translated, n_results=n_results)
            for r in results:
                parsed = self._parse_result(r)
                parsed["_language"] = lang
                parsed["_translated_query"] = translated
                all_results.append(parsed)

        seen_ids = set()
        deduped = []
        for item in all_results:
            rid = item.get("id", "")
            if rid not in seen_ids:
                seen_ids.add(rid)
                deduped.append(item)

        deduped.sort(key=lambda x: 1.0 - float(x.get("_distance", 1)), reverse=True)
        return deduped[:n_results]

    def translate_query(self, query: str, target_language: str) -> str:
        if target_language == "en":
            return query
        try:
            data = json.dumps({
                "q": query,
                "source": "auto",
                "target": target_language,
                "format": "text"
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self._libre_url}/translate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("translatedText", query)
        except Exception:
            return self._llm_translate(query, target_language)

    def multilingual_query(self, query: str, languages: list[str] = None) -> list[str]:
        languages = languages or ["en", "zh", "ja", "ko", "de", "fr", "es"]
        queries = [query]
        for lang in languages:
            if lang == "en":
                continue
            translated = self.translate_query(query, lang)
            if translated != query:
                queries.append(translated)
        return queries

    def detect_language(self, text: str) -> str:
        if not text.strip():
            return "en"

        try:
            data = json.dumps({"q": text}).encode("utf-8")
            req = urllib.request.Request(
                f"{self._libre_url}/detect",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                results = json.loads(resp.read().decode("utf-8"))
                if results and len(results) > 0:
                    return results[0].get("language", "en")
        except Exception:
            pass
        return self._heuristic_detect(text)

    def get_language_filters(self, items: list[dict], language: str) -> list[dict]:
        return [item for item in items if item.get("_language", "en") == language]

    def search_translate(self, query: str, language: str = "en", n_results: int = 20) -> list[dict]:
        if language == "en":
            return self.vector.search(query, n_results=n_results)

        translated = self.translate_query(query, "en")
        results = self.vector.search(translated, n_results=n_results)
        parsed = []
        for r in results:
            item = self._parse_result(r)
            item["_language"] = language
            item["_original_query"] = query
            item["_translated_query"] = translated
            parsed.append(item)
        return parsed

    def _heuristic_detect(self, text: str) -> str:
        scripts = {
            "zh": r"[\u4e00-\u9fff]",
            "ja": r"[\u3040-\u309f\u30a0-\u30ff]",
            "ko": r"[\uac00-\ud7af]",
            "ar": r"[\u0600-\u06ff]",
            "ru": r"[\u0400-\u04ff]",
            "de": r"[äöüß]",
            "fr": r"[éèêëàâùûüÿœæ]",
            "es": r"[ñáéíóúü]",
        }
        scores = {}
        for lang, pattern in scripts.items():
            matches = len(re.findall(pattern, text))
            if matches > 0:
                scores[lang] = matches

        if not scores:
            return "en"
        return max(scores, key=scores.get)

    def _llm_translate(self, query: str, target_language: str) -> str:
        try:
            from ..core.llm import LLMClient
            client = LLMClient()
            prompt = f"Translate the following text to {target_language}. Return only the translation, nothing else.\n\nText: {query}"
            response = client.generate(prompt)
            return response.strip()
        except Exception:
            return query

    def _parse_result(self, result: dict) -> dict:
        meta = result.get("metadata", {})
        return {
            "id": result.get("id", ""),
            "title": meta.get("title", ""),
            "content": result.get("content", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "source_type": meta.get("source_type", ""),
            "topics": meta.get("topics", "").split(",") if meta.get("topics") else [],
            "author": meta.get("author", ""),
            "published_at": meta.get("published_at", ""),
            "engagement": int(meta.get("engagement", 0) or 0),
            "_distance": float(result.get("distance", 1)),
        }
