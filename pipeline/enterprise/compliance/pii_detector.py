import re
import logging
from typing import Any

from pipeline.core.models import ContentItem

logger = logging.getLogger(__name__)


class PIIDetector:
    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_REGEX = re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}(?:\s?(?:ext|x|xtn)\s?\d{1,5})?"
    )
    CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
    SSN_REGEX = re.compile(r"\b(?:\d{3}-\d{2}-\d{4}|\d{9}|\b[STFG]\d{7}[A-Z])\b")
    IP_REGEX = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    )
    URL_AUTH_REGEX = re.compile(
        r"https?://[^\s:@]+:[^\s:@]+@[^\s]+"
    )
    API_KEY_REGEX = re.compile(
        r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|[A-Za-z0-9_-]{32,}|ghp_[A-Za-z0-9]{36,}|xox[bpsa]-[A-Za-z0-9-]{10,})\b"
    )
    TOKEN_IN_URL_REGEX = re.compile(
        r"(?:access_token|api_key|apikey|secret|token|password|passwd|auth)=[^\s&]{4,}"
    )
    BANK_ACCOUNT_REGEX = re.compile(r"\b\d{8,17}\b")

    def __init__(self, custom_patterns: list[tuple[str, str]] | None = None):
        self.patterns: list[tuple[str, re.Pattern, float]] = [
            ("email", self.EMAIL_REGEX, 0.95),
            ("phone", self.PHONE_REGEX, 0.85),
            ("credit_card", self.CREDIT_CARD_REGEX, 0.90),
            ("ssn", self.SSN_REGEX, 0.95),
            ("ip_address", self.IP_REGEX, 0.80),
            ("url_auth", self.URL_AUTH_REGEX, 0.95),
            ("api_key", self.API_KEY_REGEX, 0.90),
            ("token_in_url", self.TOKEN_IN_URL_REGEX, 0.92),
            ("bank_account", self.BANK_ACCOUNT_REGEX, 0.70),
        ]
        if custom_patterns:
            for name, pattern_str in custom_patterns:
                try:
                    self.patterns.append((name, re.compile(pattern_str), 0.50))
                except re.error as e:
                    logger.warning(f"Invalid custom pattern '{name}': {e}")

    def detect(self, text: str) -> list[dict]:
        results = []
        seen_spans = set()
        for pii_type, pattern, confidence in self.patterns:
            for match in pattern.finditer(text):
                value = match.group()
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                seen_spans.add(span)

                if pii_type == "credit_card":
                    digits_only = re.sub(r"[ -]", "", value)
                    if not self._luhn_check(digits_only):
                        continue
                    confidence = 0.95

                if pii_type == "bank_account":
                    digits_only = re.sub(r"\D", "", value)
                    if len(digits_only) < 8 or len(digits_only) > 17:
                        continue

                results.append({
                    "type": pii_type,
                    "value": value,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": confidence,
                })
        return results

    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        findings = self.detect(text)
        findings.sort(key=lambda x: x["start"], reverse=True)
        result = text
        for f in findings:
            result = result[:f["start"]] + replacement + result[f["end"]:]
        return result

    def redact_item(self, item: ContentItem) -> ContentItem:
        fields_to_redact = ["content", "title", "author_name", "author_url"]
        for field in fields_to_redact:
            val = getattr(item, field, None)
            if val and isinstance(val, str):
                setattr(item, field, self.redact(val))
        return item

    def redact_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.redact_item(item) for item in items]

    def get_stats(self, text: str) -> dict:
        findings = self.detect(text)
        types_found: dict[str, int] = {}
        for f in findings:
            types_found[f["type"]] = types_found.get(f["type"], 0) + 1
        avg_confidence = sum(f["confidence"] for f in findings) / max(len(findings), 1)
        if any(t in ("credit_card", "ssn", "api_key") for t in types_found):
            risk_level = "high"
        elif avg_confidence > 0.8 and len(findings) > 0:
            risk_level = "medium"
        else:
            risk_level = "low"
        return {
            "pii_count": len(findings),
            "types_found": types_found,
            "risk_level": risk_level,
        }

    def mask_email(self, email: str) -> str:
        match = self.EMAIL_REGEX.match(email)
        if not match:
            return email
        local, domain = email.split("@", 1)
        masked_local = local[0] + "***" if local else "***"
        return f"{masked_local}@{domain}"

    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        if not card_number.isdigit():
            return False
        total = 0
        reverse_digits = card_number[::-1]
        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0
