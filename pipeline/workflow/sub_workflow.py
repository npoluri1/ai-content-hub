from __future__ import annotations

import uuid
import copy
import time
from datetime import datetime
from typing import Any


class SubWorkflowManager:
    def __init__(self):
        self._registry: dict[str, dict] = {}
        self._execution_history: list[dict] = []
        self._builtin_templates = self._init_builtin_templates()

    def _init_builtin_templates(self) -> dict:
        return {
            "summarize_content": {
                "id": "builtin_summarize_content",
                "name": "Summarize Content",
                "description": "Input item -> summarize -> output summary",
                "type": "builtin",
                "steps": [
                    {
                        "id": "receive_input",
                        "type": "input",
                        "handler": lambda ctx: ctx.get("input_data", {}),
                    },
                    {
                        "id": "summarize",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "summary": f"Summary of: {str(ctx.get('receive_input', {}))[:200]}",
                            "original_length": len(str(ctx.get("receive_input", {}))),
                            "summary_length": 200,
                        },
                    },
                    {
                        "id": "output_result",
                        "type": "output",
                        "handler": lambda ctx: ctx.get("summarize", {}),
                    },
                ],
                "output_schema": {"summary": "string", "original_length": "int", "summary_length": "int"},
            },
            "enrich_content": {
                "id": "builtin_enrich_content",
                "name": "Enrich Content",
                "description": "Input item -> extract keywords, sentiment, category -> output enriched item",
                "type": "builtin",
                "steps": [
                    {
                        "id": "receive_input",
                        "type": "input",
                        "handler": lambda ctx: ctx.get("input_data", {}),
                    },
                    {
                        "id": "extract_keywords",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "keywords": self._extract_keywords(str(ctx.get("receive_input", {}))),
                        },
                    },
                    {
                        "id": "analyze_sentiment",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "sentiment": self._analyze_sentiment(str(ctx.get("receive_input", {}))),
                        },
                    },
                    {
                        "id": "categorize",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "category": self._categorize_content(str(ctx.get("receive_input", {}))),
                        },
                    },
                    {
                        "id": "enrich",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "enriched_item": {
                                "original": ctx.get("receive_input", {}),
                                "keywords": ctx.get("extract_keywords", {}).get("keywords", []),
                                "sentiment": ctx.get("analyze_sentiment", {}).get("sentiment", "neutral"),
                                "category": ctx.get("categorize", {}).get("category", "general"),
                                "enriched_at": datetime.utcnow().isoformat(),
                            }
                        },
                    },
                    {
                        "id": "output_result",
                        "type": "output",
                        "handler": lambda ctx: ctx.get("enrich", {}).get("enriched_item", {}),
                    },
                ],
                "output_schema": {
                    "enriched_item": {
                        "original": "any",
                        "keywords": "list",
                        "sentiment": "string",
                        "category": "string",
                        "enriched_at": "string",
                    }
                },
            },
            "classify_and_store": {
                "id": "builtin_classify_and_store",
                "name": "Classify and Store",
                "description": "Input item -> classify -> store in vector DB -> output classification",
                "type": "builtin",
                "steps": [
                    {
                        "id": "receive_input",
                        "type": "input",
                        "handler": lambda ctx: ctx.get("input_data", {}),
                    },
                    {
                        "id": "classify",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "classification": {
                                "labels": self._classify_content(str(ctx.get("receive_input", {}))),
                                "confidence": 0.85,
                            }
                        },
                    },
                    {
                        "id": "generate_embedding",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "embedding_id": f"emb_{uuid.uuid4().hex[:12]}",
                            "vector_dim": 768,
                        },
                    },
                    {
                        "id": "store_in_vector_db",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "stored": True,
                            "vector_id": f"vec_{uuid.uuid4().hex[:12]}",
                            "classification": ctx.get("classify", {}).get("classification", {}),
                        },
                    },
                    {
                        "id": "output_result",
                        "type": "output",
                        "handler": lambda ctx: {
                            "classification": ctx.get("classify", {}).get("classification", {}),
                            "vector_id": ctx.get("store_in_vector_db", {}).get("vector_id", ""),
                            "stored": True,
                        },
                    },
                ],
                "output_schema": {"classification": "dict", "vector_id": "string", "stored": "bool"},
            },
            "cross_source_dedup": {
                "id": "builtin_cross_source_dedup",
                "name": "Cross-Source Deduplication",
                "description": "Input items -> deduplicate -> merge -> output deduped items",
                "type": "builtin",
                "steps": [
                    {
                        "id": "receive_input",
                        "type": "input",
                        "handler": lambda ctx: ctx.get("input_data", {}).get("items", []),
                    },
                    {
                        "id": "normalize_items",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "normalized": [
                                {
                                    "original": item,
                                    "normalized_title": str(item.get("title", item.get("text", ""))).lower().strip(),
                                    "source": item.get("source", "unknown"),
                                }
                                for item in ctx.get("receive_input", [])
                            ]
                        },
                    },
                    {
                        "id": "detect_duplicates",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "unique_items": self._deduplicate_items(ctx.get("normalize_items", {}).get("normalized", []))
                        },
                    },
                    {
                        "id": "merge_duplicates",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "merged_items": [
                                {
                                    "title": item.get("normalized_title", ""),
                                    "sources": [item.get("source", "unknown")],
                                    "content": item.get("original", {}),
                                }
                                for item in ctx.get("detect_duplicates", {}).get("unique_items", [])
                            ]
                        },
                    },
                    {
                        "id": "output_result",
                        "type": "output",
                        "handler": lambda ctx: {
                            "items": ctx.get("merge_duplicates", {}).get("merged_items", []),
                            "total_unique": len(ctx.get("merge_duplicates", {}).get("merged_items", [])),
                            "total_original": len(ctx.get("receive_input", [])),
                        },
                    },
                ],
                "output_schema": {"items": "list", "total_unique": "int", "total_original": "int"},
            },
            "daily_digest": {
                "id": "builtin_daily_digest",
                "name": "Daily Digest",
                "description": "Input items -> group by topic -> generate digest -> output digest text",
                "type": "builtin",
                "steps": [
                    {
                        "id": "receive_input",
                        "type": "input",
                        "handler": lambda ctx: ctx.get("input_data", {}).get("items", []),
                    },
                    {
                        "id": "group_by_topic",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "groups": self._group_by_topic(ctx.get("receive_input", []))
                        },
                    },
                    {
                        "id": "rank_topics",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "ranked_groups": sorted(
                                ctx.get("group_by_topic", {}).get("groups", []),
                                key=lambda g: g.get("count", 0),
                                reverse=True,
                            )[:10]
                        },
                    },
                    {
                        "id": "generate_digest_text",
                        "type": "transform",
                        "handler": lambda ctx: {
                            "digest": self._generate_digest_text(ctx.get("rank_topics", {}).get("ranked_groups", []))
                        },
                    },
                    {
                        "id": "output_result",
                        "type": "output",
                        "handler": lambda ctx: {
                            "digest": ctx.get("generate_digest_text", {}).get("digest", ""),
                            "topic_count": len(ctx.get("rank_topics", {}).get("ranked_groups", [])),
                            "generated_at": datetime.utcnow().isoformat(),
                        },
                    },
                ],
                "output_schema": {"digest": "string", "topic_count": "int", "generated_at": "string"},
            },
        }

    def _extract_keywords(self, text: str) -> list:
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "is", "it", "this", "that"}
        words = text.lower().split()
        freq = {}
        for w in words:
            w = w.strip(".,!?;:'\"()[]{}")
            if w and w not in stop_words and len(w) > 3:
                freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: -x[1])
        return [w for w, c in sorted_words[:10]]

    def _analyze_sentiment(self, text: str) -> str:
        positive_words = {"good", "great", "excellent", "amazing", "wonderful", "fantastic", "positive", "success", "innovative", "breakthrough"}
        negative_words = {"bad", "terrible", "awful", "poor", "failure", "negative", "worst", "horrible", "problem", "crisis"}
        words = set(text.lower().split())
        pos_count = len(words & positive_words)
        neg_count = len(words & negative_words)
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def _categorize_content(self, text: str) -> str:
        categories = {
            "technology": {"ai", "software", "hardware", "cloud", "data", "code", "tech", "digital"},
            "business": {"market", "revenue", "growth", "investment", "startup", "funding", "profit"},
            "science": {"research", "study", "experiment", "lab", "discovery", "scientific"},
            "politics": {"government", "policy", "election", "law", "regulation", "president"},
            "health": {"medical", "health", "disease", "treatment", "patient", "drug"},
        }
        words = set(text.lower().split())
        best_category = "general"
        best_score = 0
        for cat, keywords in categories.items():
            score = len(words & keywords)
            if score > best_score:
                best_score = score
                best_category = cat
        return best_category

    def _classify_content(self, text: str) -> list:
        categories = {
            "technology": {"ai", "software", "hardware", "cloud", "data", "code", "tech", "digital", "algorithm", "api", "framework"},
            "business": {"market", "revenue", "growth", "investment", "startup", "funding", "profit", "acquisition", "ipo"},
            "science": {"research", "study", "experiment", "lab", "discovery", "scientific", "hypothesis", "theory"},
            "politics": {"government", "policy", "election", "law", "regulation", "president", "senate", "congress"},
            "health": {"medical", "health", "disease", "treatment", "patient", "drug", "clinical", "therapy"},
        }
        words = set(text.lower().split())
        labels = []
        for cat, keywords in categories.items():
            if len(words & keywords) >= 2:
                labels.append(cat)
        return labels if labels else ["general"]

    def _deduplicate_items(self, items: list) -> list:
        seen = set()
        unique = []
        for item in items:
            key = item.get("normalized_title", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _group_by_topic(self, items: list) -> list:
        topic_keywords = {
            "AI & Machine Learning": {"ai", "machine learning", "deep learning", "neural", "gpt", "llm", "transformer"},
            "Cloud & Infrastructure": {"cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops"},
            "Cybersecurity": {"security", "cyber", "vulnerability", "breach", "encryption", "malware"},
            "Software Development": {"javascript", "python", "rust", "typescript", "react", "framework"},
            "Data & Analytics": {"data", "analytics", "big data", "database", "sql", "nosql"},
        }
        groups = {}
        for topic, keywords in topic_keywords.items():
            topic_items = []
            for item in items:
                text = str(item.get("normalized_title", "") or "")
                if any(kw in text for kw in keywords):
                    topic_items.append(item)
            if topic_items:
                groups[topic] = {"topic": topic, "items": topic_items, "count": len(topic_items)}
        return list(groups.values())

    def _generate_digest_text(self, groups: list) -> str:
        lines = ["# Daily Digest", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        for group in groups:
            lines.append(f"## {group['topic']} ({group['count']} items)")
            for item in group["items"][:5]:
                title = item.get("normalized_title", "Untitled")
                source = item.get("source", "unknown")
                lines.append(f"- {title} [{source}]")
            lines.append("")
        return "\n".join(lines)

    def register(self, sub_workflow: dict, parent_workflow_id: str = None) -> str:
        sub_workflow_id = sub_workflow.get("id") or f"sw_{uuid.uuid4().hex[:12]}"
        entry = {
            "id": sub_workflow_id,
            "workflow": copy.deepcopy(sub_workflow),
            "parent_workflow_id": parent_workflow_id,
            "registered_at": datetime.utcnow().isoformat(),
            "type": sub_workflow.get("type", "custom"),
            "execution_count": 0,
        }
        self._registry[sub_workflow_id] = entry
        return sub_workflow_id

    def unregister(self, sub_workflow_id: str) -> bool:
        if sub_workflow_id in self._registry and self._registry[sub_workflow_id]["type"] != "builtin":
            del self._registry[sub_workflow_id]
            return True
        return False

    def list(self, include_builtin: bool = True) -> list[dict]:
        results = []
        for sw_id, entry in self._registry.items():
            results.append(entry)
        if include_builtin:
            for tmpl_id, tmpl in self._builtin_templates.items():
                if tmpl_id not in self._registry:
                    results.append(tmpl)
        return results

    def execute(self, sub_workflow_id: str, input_data: dict, parent_context: dict = None) -> dict:
        sub = self._registry.get(sub_workflow_id)
        if not sub:
            sub = self._builtin_templates.get(sub_workflow_id)
            if not sub:
                raise ValueError(f"Sub-workflow '{sub_workflow_id}' not found")
        context = {
            "input_data": copy.deepcopy(input_data),
            "parent_context": copy.deepcopy(parent_context or {}),
            "sub_workflow_id": sub_workflow_id,
            "started_at": datetime.utcnow().isoformat(),
        }
        steps = sub.get("steps", [])
        for step in steps:
            handler = step.get("handler")
            if handler:
                try:
                    result = handler(context)
                    context[step["id"]] = result
                except Exception as e:
                    context[step["id"]] = {"error": str(e)}
                    raise
        output = context.get("output_result", context)
        if sub_workflow_id in self._registry:
            self._registry[sub_workflow_id]["execution_count"] += 1
        self._execution_history.append({
            "sub_workflow_id": sub_workflow_id,
            "input": input_data,
            "output": output,
            "executed_at": datetime.utcnow().isoformat(),
        })
        return output

    def create_from_template(self, name: str, template_type: str, config: dict) -> dict:
        template = self._builtin_templates.get(template_type)
        if not template:
            raise ValueError(f"Unknown template type: {template_type}")
        new_id = f"sw_{uuid.uuid4().hex[:12]}"
        new_workflow = copy.deepcopy(template)
        new_workflow["id"] = new_id
        new_workflow["name"] = name
        new_workflow["type"] = "custom"
        new_workflow["created_at"] = datetime.utcnow().isoformat()
        for key, value in config.items():
            if key in new_workflow:
                new_workflow[key] = value
        self.register(new_workflow)
        return self._registry[new_id]

    def get_execution_history(self, sub_workflow_id: str = None, limit: int = 50) -> list[dict]:
        if sub_workflow_id:
            return [h for h in self._execution_history if h["sub_workflow_id"] == sub_workflow_id][-limit:]
        return self._execution_history[-limit:]

    def chain(self, sub_workflow_ids: list[str], initial_input: dict) -> list[dict]:
        outputs = []
        current_input = initial_input
        for sw_id in sub_workflow_ids:
            output = self.execute(sw_id, current_input)
            outputs.append({"sub_workflow_id": sw_id, "output": output})
            current_input = output
        return outputs
