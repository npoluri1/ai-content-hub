import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional

from pipeline.core.models import ContentItem

logger = logging.getLogger(__name__)


class DataClassifier:
    RESTRICTED_PATTERNS = [
        (re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36,})\b"), "api_key"),
        (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "internal_ip"),
        (re.compile(r"(?:api_key|apikey|secret|token|password|passwd)=[^\s&]{4,}"), "credential_in_url"),
        (re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b"), "private_ip"),
        (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "pii_email"),
        (re.compile(r"\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b"), "pii_ssn"),
    ]

    CONFIDENTIAL_PATTERNS = [
        (re.compile(r"\b(?:revenue|budget|financial|profit|loss)\s*:?\s*\d+[kKmMbB]?\b", re.IGNORECASE), "financial_data"),
        (re.compile(r"\b(?:unreleased|planned|roadmap|upcoming\s+feature|alpha|beta\s+test)\b", re.IGNORECASE), "unreleased_product"),
        (re.compile(r"\b(?:strategy|strategic|strategic\s+plan|initiative)\b", re.IGNORECASE), "strategy_doc"),
        (re.compile(r"\b(?:project\s+[A-Z][a-z]+|internal\s+project)\b"), "internal_project"),
    ]

    INTERNAL_PATTERNS = [
        (re.compile(r"\b(?:CompanyName|AcmeCorp|OurPlatform|OurApp)\b", re.IGNORECASE), "company_name"),
        (re.compile(r"\b(?:internal\s+tool|admin\s+panel|internal\s+dashboard)\b", re.IGNORECASE), "internal_tool"),
        (re.compile(r"\b(?:team\s+\w+|engineering|marketing|sales|design)\s+team\b", re.IGNORECASE), "team_name"),
    ]

    PUBLIC_PATTERNS = [
        (re.compile(r"\b(?:published|announced|released)\b", re.IGNORECASE), "public_announcement"),
        (re.compile(r"\b(?:news|press\s+release|blog)\b", re.IGNORECASE), "public_source"),
    ]

    def __init__(self, rules_path: str = "./data/classification/rules.json"):
        self.rules_path = rules_path
        os.makedirs(os.path.dirname(os.path.abspath(self.rules_path)), exist_ok=True)
        self._custom_rules: list[dict] = []
        self._load_custom_rules()
        self._classified_log: list[dict] = []

    def _load_custom_rules(self):
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r") as f:
                    self._custom_rules = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load custom rules: {e}")

    def _save_custom_rules(self):
        with open(self.rules_path, "w") as f:
            json.dump(self._custom_rules, f, indent=2)

    @staticmethod
    def _match_patterns(text: str, patterns: list[tuple[re.Pattern, str]]) -> list[dict]:
        flags = []
        for pattern, label in patterns:
            if pattern.search(text):
                flags.append({"pattern": label, "matched": True})
        return flags

    def classify(self, text: str) -> dict:
        factors = []
        flags = []

        restricted_flags = self._match_patterns(text, self.RESTRICTED_PATTERNS)
        confidential_flags = self._match_patterns(text, self.CONFIDENTIAL_PATTERNS)
        internal_flags = self._match_patterns(text, self.INTERNAL_PATTERNS)
        public_flags = self._match_patterns(text, self.PUBLIC_PATTERNS)

        for rule in self._custom_rules:
            try:
                pattern = re.compile(rule["pattern"])
                if pattern.search(text):
                    flags.append({"rule": rule["name"], "level": rule["level"], "matched": True})
            except re.error:
                continue

        if restricted_flags:
            level = "restricted"
            factors = ["credentials", "pii", "internal_ip"]
            flags.extend(restricted_flags)
        elif confidential_flags:
            level = "confidential"
            factors = ["financial_data", "unreleased_product", "strategy"]
            flags.extend(confidential_flags)
        elif internal_flags:
            level = "internal"
            factors = ["company_name", "internal_tool", "team_name"]
            flags.extend(internal_flags)
        elif public_flags:
            level = "public"
            factors = ["public_announcement", "public_source"]
            flags.extend(public_flags)
        else:
            level = "public"
            factors = ["no_sensitive_content"]
            flags.append({"pattern": "default_public", "matched": False})

        score_map = {"restricted": 0.95, "confidential": 0.75, "internal": 0.50, "public": 0.10}
        score = score_map.get(level, 0.10)

        return {"level": level, "score": score, "factors": factors, "flags": flags}

    def classify_item(self, item: ContentItem) -> ContentItem:
        text = f"{item.title} {item.content} {item.source} {' '.join(item.topics) if item.topics else ''}"
        classification = self.classify(text)
        item.metadata["classification"] = classification
        item.metadata["classified_at"] = datetime.utcnow().isoformat()
        self._classified_log.append({
            "id": item.id,
            "level": classification["level"],
            "classified_at": datetime.utcnow().isoformat(),
        })
        return item

    def classify_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.classify_item(item) for item in items]

    def set_custom_rule(self, name: str, pattern: str, level: str) -> bool:
        if level not in ("public", "internal", "confidential", "restricted"):
            logger.error(f"Invalid classification level: {level}")
            return False
        try:
            re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return False
        self._custom_rules.append({"name": name, "pattern": pattern, "level": level})
        self._save_custom_rules()
        logger.info(f"Custom rule added: {name} -> {level}")
        return True

    def get_classification_distribution(self, days: int = 30) -> dict:
        cutoff = datetime.utcnow() - timedelta(days=days)
        distribution = {"restricted": 0, "confidential": 0, "internal": 0, "public": 0}
        for entry in self._classified_log:
            entry_time = datetime.fromisoformat(entry["classified_at"])
            if entry_time >= cutoff:
                level = entry["level"]
                if level in distribution:
                    distribution[level] += 1
        distribution["total"] = sum(distribution.values())
        return distribution

    def get_items_by_level(self, level: str, limit: int = 50) -> list[dict]:
        if level not in ("public", "internal", "confidential", "restricted"):
            return []
        items = [e for e in self._classified_log if e["level"] == level]
        return items[:limit]
