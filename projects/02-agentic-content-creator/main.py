"""
Multi-agent content creation pipeline with security gates.
"""

from typing import TypedDict

class ContentState(TypedDict):
    topic: str
    research: str
    draft: str
    reviewed: str
    approved: bool

class ResearchAgent:
    def run(self, topic: str) -> str:
        return f"Research findings on {topic}: 3 key trends identified"

class WriterAgent:
    def run(self, research: str) -> str:
        return f"Draft article based on: {research[:50]}..."

class ReviewAgent:
    def run(self, draft: str) -> str:
        return f"Reviewed: {draft[:50]}... [2 minor corrections made]"

class ApprovalGate:
    def __init__(self):
        self.approvals = []

    def request(self, content: str) -> str:
        import hashlib, time
        aid = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.approvals.append({"id": aid, "content": content, "status": "pending"})
        return aid

    def approve(self, aid: str) -> bool:
        for a in self.approvals:
            if a["id"] == aid:
                a["status"] = "approved"
                return True
        return False

research_agent = ResearchAgent()
writer_agent = WriterAgent()
review_agent = ReviewAgent()
approval_gate = ApprovalGate()

topic = "AI Agent Security in 2026"
research = research_agent.run(topic)
draft = writer_agent.run(research)
review = review_agent.run(draft)
approval_id = approval_gate.request(review)

print(f"Research:\n{research}\n")
print(f"Draft:\n{draft}\n")
print(f"Review:\n{review}\n")
print(f"Approval needed: {approval_id}")
approval_gate.approve(approval_id)
print("Content approved and ready to publish.")
