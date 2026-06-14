import json
import logging
import os
import re
from typing import Any

from pipeline.core.models import ContentItem

logger = logging.getLogger(__name__)

DEFAULT_TERMS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "moderation_terms.json")

PROFANITY_LIST = [
    "fuck", "shit", "ass", "bitch", "damn", "bastard", "crap", "dick", "piss",
    "slut", "whore", "cunt", "douche", "cock", "screw", "bloody", "bugger",
    "arse", "jerk", "moron", "idiot", "stupid", "retard", "loser", "prick",
    "wanker", "bollocks", "git", "twat", "bellend", "shithead", "motherfucker",
    "asshole", "dipshit", "dumbass", "jackass", "sonofabitch", "goddamn",
    "bullshit", "nutsack", "tits", "boobs", "porn", "xxx", "sex", "faggot",
    "nigger", "spic", "chink", "kike", "gook",
]


class ContentModerator:
    def __init__(self, terms_path: str | None = None):
        self.terms_path = terms_path or DEFAULT_TERMS_PATH
        self._thresholds: dict[str, float] = {
            "profanity": 0.7,
            "spam": 0.6,
            "hate_speech": 0.8,
            "harassment": 0.7,
            "self_promotion": 0.6,
            "misinformation": 0.7,
        }
        self._load_terms()

    def _get_terms_path(self):
        path = self.terms_path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return path

    def _load_terms(self):
        path = self._get_terms_path()
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self._custom_terms: dict[str, list[str]] = data.get("terms", {})
            except Exception:
                self._custom_terms = {}
        else:
            self._custom_terms = {}
            self._save_terms()

    def _save_terms(self):
        path = self._get_terms_path()
        with open(path, "w") as f:
            json.dump({"terms": self._custom_terms}, f, indent=2)

    def moderate(self, text: str) -> dict:
        text_lower = text.lower()
        flags = []

        profanity_flag = self._check_profanity(text_lower)
        if profanity_flag:
            flags.append(profanity_flag)

        spam_flag = self._check_spam(text, text_lower)
        if spam_flag:
            flags.append(spam_flag)

        hate_flag = self._check_hate_speech(text_lower)
        if hate_flag:
            flags.append(hate_flag)

        harassment_flag = self._check_harassment(text_lower)
        if harassment_flag:
            flags.append(harassment_flag)

        promo_flag = self._check_self_promotion(text_lower)
        if promo_flag:
            flags.append(promo_flag)

        misinfo_flag = self._check_misinformation(text_lower)
        if misinfo_flag:
            flags.append(misinfo_flag)

        approved = True
        for flag in flags:
            threshold = self._thresholds.get(flag["type"], 0.7)
            if flag["confidence"] >= threshold:
                approved = False

        score = sum(f["confidence"] for f in flags) / max(len(flags), 1) if flags else 0.0

        return {
            "approved": approved,
            "flags": flags,
            "score": round(min(score, 1.0), 4),
        }

    def moderate_item(self, item: ContentItem) -> ContentItem:
        result = self.moderate(item.content + " " + item.title)
        item.metadata["moderation"] = result
        return item

    def moderate_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.moderate_item(item) for item in items]

    def get_blocked_terms(self) -> list[str]:
        all_terms = set(PROFANITY_LIST)
        for terms in self._custom_terms.values():
            all_terms.update(terms)
        return sorted(all_terms)

    def add_blocked_term(self, term: str, category: str = "custom") -> bool:
        term_lower = term.lower().strip()
        if not term_lower:
            return False
        if category not in self._custom_terms:
            self._custom_terms[category] = []
        if term_lower not in self._custom_terms[category]:
            self._custom_terms[category].append(term_lower)
            self._save_terms()
            return True
        return False

    def remove_blocked_term(self, term: str) -> bool:
        term_lower = term.lower().strip()
        for category, terms in self._custom_terms.items():
            if term_lower in terms:
                self._custom_terms[category] = [t for t in terms if t != term_lower]
                self._save_terms()
                return True
        return False

    def set_threshold(self, category: str, threshold: float) -> bool:
        if category not in self._thresholds:
            return False
        self._thresholds[category] = max(0.0, min(1.0, threshold))
        return True

    def _check_profanity(self, text_lower: str) -> dict | None:
        for word in PROFANITY_LIST:
            if re.search(rf"\b{re.escape(word)}\b", text_lower):
                return {"type": "profanity", "word": word, "confidence": 0.9}
        for terms in self._custom_terms.values():
            for word in terms:
                if re.search(rf"\b{re.escape(word)}\b", text_lower):
                    return {"type": "profanity", "word": word, "confidence": 0.85}
        return None

    def _check_spam(self, text: str, text_lower: str) -> dict | None:
        urls = re.findall(r"https?://[^\s]+", text)
        if not urls:
            return None
        url_ratio = len(" ".join(urls)) / max(len(text), 1)
        if url_ratio > 0.30:
            return {"type": "spam", "word": "excessive_urls", "confidence": 0.85}
        repeated = re.search(r"(.)\1{5,}", text)
        if repeated:
            return {"type": "spam", "word": "repeated_chars", "confidence": 0.75}
        upper_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if upper_ratio > 0.50 and len(text) > 20:
            return {"type": "spam", "word": "excessive_caps", "confidence": 0.70}
        return None

    def _check_hate_speech(self, text_lower: str) -> dict | None:
        hate_terms = ["nigger", "faggot", "spic", "chink", "kike", "gook", "white power", "heil hitler"]
        for term in hate_terms:
            if term in text_lower:
                return {"type": "hate_speech", "word": term, "confidence": 0.95}
        return None

    def _check_harassment(self, text_lower: str) -> dict | None:
        harassment_patterns = [
            r"\bkill\s+(yourself|urself)\b",
            r"\bgo\s+(die|kill)\b",
            r"\bend\s+(yourself|urself)\b",
            r"\bharm\s+(yourself|urself)\b",
        ]
        for pattern in harassment_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return {"type": "harassment", "word": match.group(), "confidence": 0.9}
        return None

    def _check_self_promotion(self, text_lower: str) -> dict | None:
        promo_domains = re.findall(r"https?://([^\s/]+)", text_lower)
        domain_counts: dict[str, int] = {}
        for domain in promo_domains:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        for domain, count in domain_counts.items():
            if count >= 3 and not any(
                d in domain for d in ["reddit.com", "linkedin.com", "twitter.com", "github.com"]
            ):
                return {"type": "self_promotion", "word": domain, "confidence": 0.85}
        return None

    def _check_misinformation(self, text_lower: str) -> dict | None:
        misinfo_terms = [
            r"\b5g\s*causes\s*covid\b",
            r"\bearth\s*is\s*flat\b",
            r"\bvaccines?\s*cause\s*autism\b",
            r"\bchemtrails?\b",
            r"\bqanon\b",
            r"\bbill\s*gates\s*(depopulate|microchip)\b",
        ]
        for pattern in misinfo_terms:
            if re.search(pattern, text_lower):
                return {"type": "misinformation", "word": pattern.replace("\\s*", " "), "confidence": 0.85}
        return None
