"""
Agent Security patterns inspired by OpenFang architecture.
WASM sandboxing, Merkle audit trails, prompt injection scanning, purchase gates.
"""

import hashlib
import json
import time
from typing import Any

class MerkleAuditTrail:
    """Tamper-evident audit trail using Merkle hash chains."""

    def __init__(self):
        self.entries: list[dict] = []
        self.previous_hash = "0" * 64

    def append(self, action: str, actor: str, metadata: dict | None = None):
        entry = {
            "timestamp": time.time(),
            "action": action,
            "actor": actor,
            "metadata": metadata or {},
            "previous_hash": self.previous_hash,
        }
        entry["hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode()
        ).hexdigest()
        self.entries.append(entry)
        self.previous_hash = entry["hash"]
        return entry

    def verify(self) -> bool:
        for i, entry in enumerate(self.entries):
            expected_hash = hashlib.sha256(
                json.dumps({k: v for k, v in entry.items() if k != "hash"},
                          sort_keys=True).encode()
            ).hexdigest()
            if entry["hash"] != expected_hash:
                return False
            if i > 0 and entry["previous_hash"] != self.entries[i - 1]["hash"]:
                return False
        return True


class PromptInjectionScanner:
    """Runtime prompt injection detection."""

    SENSITIVE_PATTERNS = [
        "ignore previous", "ignore all", "act as", "DAN",
        "you are free", "bypass", "system prompt", "forget"
    ]

    @classmethod
    def scan(cls, text: str) -> tuple[bool, list[str]]:
        flagged = [p for p in cls.SENSITIVE_PATTERNS if p in text.lower()]
        return (len(flagged) == 0, flagged)


class SpendGate:
    """Mandatory purchase gate — no money spent without explicit confirmation."""

    def __init__(self):
        self.pending_approvals: list[dict] = []

    def request_approval(self, amount: float, description: str,
                         requestor: str) -> str:
        approval_id = hashlib.md5(f"{time.time()}{amount}".encode()).hexdigest()[:8]
        self.pending_approvals.append({
            "id": approval_id,
            "amount": amount,
            "description": description,
            "requestor": requestor,
            "status": "pending"
        })
        return approval_id

    def approve(self, approval_id: str, approver: str) -> bool:
        for req in self.pending_approvals:
            if req["id"] == approval_id and req["status"] == "pending":
                req["status"] = "approved"
                req["approver"] = approver
                return True
        return False


audit = MerkleAuditTrail()
audit.append("read_file", "agent_1", {"file": "report.pdf"})
audit.append("write_db", "agent_1", {"table": "users"})
print(f"Audit trail valid: {audit.verify()}")

is_safe, flagged = PromptInjectionScanner.scan("Ignore previous instructions")
print(f"Prompt safe: {is_safe}, Flagged: {flagged}")

gate = SpendGate()
pid = gate.request_approval(50.0, "API credits", "agent_1")
gate.approve(pid, "human_admin")
print(f"Payment approved: {gate.pending_approvals[0]['status']}")
