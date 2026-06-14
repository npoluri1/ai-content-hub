"""Extract relationships between entities using pattern matching and proximity."""

from ..core.models import ContentItem
from collections import defaultdict, Counter
import json
import math
import re


RELATION_PATTERNS = [
    (r'\b(\w+(?:\s+\w+)?)\s+(?:works at|is employed by|is an? (?:engineer|scientist|researcher|developer) at|is part of|is with|joined)\s+(\w+(?:\s+\w+)?)', "works_at"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:founded|co-founded|started|created|established|launched)\s+(\w+(?:\s+\w+)?)', "founded"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:acquired|purchased|bought|took over)\s+(\w+(?:\s+\w+)?)', "acquired"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:partnered with|entered into a partnership with|formed an alliance with|teamed up with|collaborated with)\s+(\w+(?:\s+\w+)?)', "partnered_with"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:released|shipped|launched|unveiled|announced|introduced)\s+(\w+(?:\s+\w+)?)', "released"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:competes with|rivals|is a rival of|is competing against)\s+(\w+(?:\s+\w+)?)', "competes_with"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:invested in|led|participated in|funded|backed)\s+(\w+(?:\s+\w+)?)', "invested_in"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:collaborates with|collaborated with|works with|worked with|partners with)\s+(\w+(?:\s+\w+)?)', "collaborates_with"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:leads|is the (?:CEO|CTO|CFO|COO|VP|director|head|chief|president|founder|chairman|managing director) of|is leading)\s+(\w+(?:\s+\w+)?)', "leads"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:develops|developed|builds|built|creates|created|designs|designed)\s+(\w+(?:\s+\w+)?)', "develops"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:uses|used|utilizes|utilized|leverages|leveraged|employs|employed|adopts|adopted|integrates|integrated)\s+(\w+(?:\s+\w+)?)', "uses"),
    (r'\b(\w+(?:\s+\w+)?)\s+(?:is a\s+(\w+)\s+at)\s+(\w+(?:\s+\w+)?)', "works_at"),
    (r'\b(?:CEO|CTO|CFO|COO|VP|director|head|chief|president|founder|chairman)\s+(\w+(?:\s+\w+)?)\s+(?:of|at)\s+(\w+(?:\s+\w+)?)', "leads"),
    (r'\b(\w+(?:\s+\w+)?)\s+(\w+(?:\s+\w+)?)\s+(?:announced|unveiled|introduced|presented)\s+(\w+(?:\s+\w+)?)', "released"),
]

RELATION_ALIASES = {
    "works at": "works_at",
    "employed by": "works_at",
    "works for": "works_at",
    "is part of": "works_at",
    "joined": "works_at",
    "founded": "founded",
    "co-founded": "founded",
    "started": "founded",
    "acquired": "acquired",
    "bought": "acquired",
    "partnered with": "partnered_with",
    "teamed up with": "partnered_with",
    "collaborated with": "collaborates_with",
    "released": "released",
    "launched": "released",
    "unveiled": "released",
    "introduced": "released",
    "competes with": "competes_with",
    "invested in": "invested_in",
    "funded": "invested_in",
    "backed": "invested_in",
    "leads": "leads",
    "heads": "leads",
    "develops": "develops",
    "builds": "develops",
    "uses": "uses",
    "leveraging": "uses",
    "integrates": "uses",
}


class RelationExtractor:
    def __init__(self):
        self._cache = {}

    def extract(self, text: str, entities: list[dict] = None) -> list[dict]:
        if not text or not text.strip():
            return []
        cache_key = hash(text[:200])
        if cache_key in self._cache:
            return self._cache[cache_key]

        relations = []

        relations.extend(self._extract_patterns(text))
        relations.extend(self._extract_by_proximity(text, entities))

        deduped = self._deduplicate(relations)
        deduped.sort(key=lambda r: r.get("confidence", 0), reverse=True)
        self._cache[cache_key] = deduped
        return deduped

    def _extract_patterns(self, text: str) -> list[dict]:
        relations = []
        for pattern_str, relation_type in RELATION_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) >= 2:
                    subject = groups[0].strip()
                    object_ = groups[-1].strip()
                    if subject.lower() == object_.lower():
                        continue
                    sentence = self._extract_sentence(text, match.start())
                    relations.append({
                        "subject": subject,
                        "subject_type": self._infer_type(subject),
                        "relation": relation_type,
                        "object": object_,
                        "object_type": self._infer_type(object_),
                        "confidence": self._pattern_confidence(relation_type, match),
                        "sentence": sentence,
                    })
        return relations

    def _pattern_confidence(self, relation_type: str, match: re.Match) -> float:
        base_confidences = {
            "works_at": 0.85, "founded": 0.9, "acquired": 0.95,
            "partnered_with": 0.88, "released": 0.85, "competes_with": 0.8,
            "invested_in": 0.85, "collaborates_with": 0.8, "leads": 0.9,
            "develops": 0.75, "uses": 0.7,
        }
        base = base_confidences.get(relation_type, 0.7)
        span = match.end() - match.start()
        length_factor = min(1.0, span / 10)
        return round(base * length_factor, 4)

    def _extract_by_proximity(self, text: str, entities: list[dict] = None) -> list[dict]:
        if not entities:
            return []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        relations = []

        for sent in sentences:
            sent_entities = [e for e in entities if e.get("text", "") in sent]
            if len(sent_entities) < 2:
                continue

            for i in range(len(sent_entities)):
                for j in range(i + 1, len(sent_entities)):
                    ei = sent_entities[i]
                    ej = sent_entities[j]
                    ei_text = ei.get("text", "")
                    ej_text = ej.get("text", "")
                    if ei_text.lower() == ej_text.lower():
                        continue

                    ei_pos = sent.lower().find(ei_text.lower())
                    ej_pos = sent.lower().find(ej_text.lower())
                    if ei_pos < 0 or ej_pos < 0:
                        continue

                    between = sent[ei_pos + len(ei_text):ej_pos] if ei_pos < ej_pos else sent[ej_pos + len(ej_text):ei_pos]
                    between_lower = between.lower()

                    found_relation = "collaborates_with"
                    confidence = 0.4

                    for alias, rel_type in sorted(RELATION_ALIASES.items(), key=lambda x: -len(x[0])):
                        if alias in between_lower:
                            found_relation = rel_type
                            confidence = 0.6
                            break

                    if ei_pos < ej_pos:
                        subj, obj = ei, ej
                    else:
                        subj, obj = ej, ei

                    relations.append({
                        "subject": subj.get("text", ""),
                        "subject_type": subj.get("type", self._infer_type(subj.get("text", ""))),
                        "relation": found_relation,
                        "object": obj.get("text", ""),
                        "object_type": obj.get("type", self._infer_type(obj.get("text", ""))),
                        "confidence": confidence,
                        "sentence": sent.strip(),
                    })

        return relations

    def _extract_sentence(self, text: str, pos: int) -> str:
        start = max(0, text.rfind(".", 0, pos) + 1)
        end = text.find(".", pos)
        if end == -1:
            end = text.find("!", pos)
        if end == -1:
            end = text.find("?", pos)
        if end == -1:
            end = len(text)
        else:
            end += 1
        return text[start:end].strip()

    def _infer_type(self, entity_text: str) -> str:
        entity_lower = entity_text.lower()
        from .enhanced_ner import AI_COMPANIES, TECH_COMPANIES, AI_RESEARCHERS, AI_PRODUCTS
        if entity_lower in AI_COMPANIES or entity_lower in TECH_COMPANIES:
            return "ORGANIZATION"
        if entity_lower in AI_PRODUCTS:
            return "PRODUCT"
        if entity_lower in AI_RESEARCHERS:
            return "PERSON"
        if entity_lower[0].isupper() and " " in entity_lower and not entity_lower.startswith("http"):
            return "PERSON"
        if any(t in entity_lower for t in ["gpt", "llm", "ai", "model", "api", "sdk"]):
            return "TECHNOLOGY"
        return "ORGANIZATION"

    def _deduplicate(self, relations: list[dict]) -> list[dict]:
        seen = set()
        deduped = []
        for r in relations:
            key = (r["subject"].lower(), r["relation"], r["object"].lower())
            if key in seen:
                for existing in deduped:
                    ekey = (existing["subject"].lower(), existing["relation"], existing["object"].lower())
                    if ekey == key and r["confidence"] > existing["confidence"]:
                        existing["confidence"] = r["confidence"]
                        existing["sentence"] = r["sentence"]
                continue
            seen.add(key)
            deduped.append(r)
        return deduped

    def extract_item(self, item: ContentItem) -> ContentItem:
        text = f"{item.title} {item.content}"
        entities = item.metadata.get("entities", [])
        relations = self.extract(text, entities)
        item.metadata["relations"] = relations

        relation_counts = Counter(r["relation"] for r in relations)
        item.metadata["relation_count"] = len(relations)
        item.metadata["relation_types"] = dict(relation_counts.most_common())
        return item

    def extract_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.extract_item(item) for item in items]

    def get_relation_graph(self, entity: str, depth: int = 2, limit: int = 50) -> dict:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=2000)

        entity_lower = entity.lower()
        nodes = {entity_lower: {"name": entity, "type": self._infer_type(entity), "count": 0}}
        edges = []
        queue = [(entity_lower, 0)]
        visited = set()

        while queue:
            current, d = queue.pop(0)
            if d >= depth or current in visited:
                continue
            visited.add(current)

            for r in results:
                text = (r.get("title", "") + " " + r.get("content", "")).lower()
                if current not in text:
                    continue
                meta_raw = r.get("metadata", "{}")
                if isinstance(meta_raw, str):
                    try:
                        meta = json.loads(meta_raw)
                    except (json.JSONDecodeError, TypeError):
                        continue
                else:
                    meta = meta_raw

                relations = meta.get("relations", [])
                for rel in relations:
                    subj = rel.get("subject", "").lower()
                    obj = rel.get("object", "").lower()
                    opp = None
                    if subj == current and obj:
                        opp = obj
                    elif obj == current and subj:
                        opp = subj

                    if opp and opp != current:
                        nodes.setdefault(opp, {"name": rel.get("object" if subj == current else "subject", opp), "type": rel.get("object_type" if subj == current else "subject_type", self._infer_type(opp)), "count": 0})
                        nodes[opp]["count"] += 1
                        edges.append({"source": current, "target": opp, "relation": rel.get("relation", "related_to"), "sentence": rel.get("sentence", "")[:100]})

                        if d + 1 < depth:
                            queue.append((opp, d + 1))

                if len(edges) >= limit:
                    break
            if len(edges) >= limit:
                break

        node_list = [{"name": v["name"], "type": v["type"], "connections": v["count"]} for v in nodes.values()]
        return {"center": entity, "nodes": node_list, "edges": edges[:limit]}

    def get_entity_connections(self, entity: str) -> list[dict]:
        graph = self.get_relation_graph(entity, depth=1, limit=100)
        return graph.get("edges", [])

    def find_path_between(self, entity_a: str, entity_b: str, max_depth: int = 3) -> list[list[dict]]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=3000)

        ea_lower = entity_a.lower()
        eb_lower = entity_b.lower()
        adjacency = defaultdict(list)

        for r in results:
            meta_raw = r.get("metadata", "{}")
            if isinstance(meta_raw, str):
                try:
                    meta = json.loads(meta_raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            else:
                meta = meta_raw
            relations = meta.get("relations", [])
            for rel in relations:
                subj = rel.get("subject", "").lower()
                obj = rel.get("object", "").lower()
                if subj and obj and subj != obj:
                    adjacency[subj].append((obj, rel.get("relation", "related_to"), rel.get("sentence", "")))
                    adjacency[obj].append((subj, rel.get("relation", "related_to"), rel.get("sentence", "")))

        paths = []
        queue = [([(ea_lower, "start", "")], set())]

        while queue:
            path, visited = queue.pop(0)
            last_node = path[-1][0]

            if last_node == eb_lower:
                paths.append(path)
                continue

            if len(path) > max_depth:
                continue

            for neighbor, rel, sent in adjacency.get(last_node, []):
                if neighbor in visited:
                    continue
                new_path = path + [(neighbor, rel, sent)]
                new_visited = visited | {neighbor}
                queue.append((new_path, new_visited))

        result = []
        for path in paths[:10]:
            formatted = []
            for node, rel, sent in path:
                formatted.append({"entity": node, "relation": rel, "sentence": sent[:80]})
            result.append(formatted)

        return result

    def get_relation_stats(self) -> dict:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=5000)

        type_counts = Counter()
        total = 0

        for r in results:
            meta_raw = r.get("metadata", "{}")
            if isinstance(meta_raw, str):
                try:
                    meta = json.loads(meta_raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            else:
                meta = meta_raw
            relations = meta.get("relations", [])
            for rel in relations:
                type_counts[rel.get("relation", "unknown")] += 1
                total += 1

        return {
            "total_relations": total,
            "relation_types": dict(type_counts.most_common()),
            "unique_types": len(type_counts),
        }

    def search_by_relation(self, relation: str, entity: str = None, limit: int = 20) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=2000)
        matches = []

        for r in results:
            meta_raw = r.get("metadata", "{}")
            if isinstance(meta_raw, str):
                try:
                    meta = json.loads(meta_raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            else:
                meta = meta_raw
            relations = meta.get("relations", [])
            for rel in relations:
                if rel.get("relation") != relation:
                    continue
                if entity:
                    e_lower = entity.lower()
                    if e_lower not in rel.get("subject", "").lower() and e_lower not in rel.get("object", "").lower():
                        continue
                matches.append({
                    "item_id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "relation": rel,
                })
                if len(matches) >= limit:
                    break
            if len(matches) >= limit:
                break

        return matches
