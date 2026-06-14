import uuid
import json
from datetime import datetime
from .nodes import NodeType, create_node, WorkflowNode


class WorkflowBuilder:
    def __init__(self, name=None, description=None):
        self.name = name or "Untitled Workflow"
        self.description = description or ""
        self.nodes = {}
        self.edges = []

    def add_trigger(self, schedule, source=None, topic=None):
        node = create_node(NodeType.TRIGGER, "Trigger", {
            "schedule": schedule, "source": source, "topic": topic
        })
        self.nodes[node.id] = node
        return self

    def add_collector(self, source, max_items=50, query=None):
        node = create_node(NodeType.COLLECT, "Collector", {
            "source": source, "max_items": max_items, "query": query
        })
        self.nodes[node.id] = node
        return self

    def add_filter(self, min_relevance=0.3, topics=None, condition=None):
        node = create_node(NodeType.FILTER, "Filter", {
            "min_relevance": min_relevance, "topics": topics or [], "condition": condition or ""
        })
        self.nodes[node.id] = node
        return self

    def add_classifier(self, method="hybrid"):
        node = create_node(NodeType.CLASSIFY, "Classifier", {
            "method": method
        })
        self.nodes[node.id] = node
        return self

    def add_notifier(self, channel, template=None, recipients=None):
        node = create_node(NodeType.NOTIFY, "Notifier", {
            "channel": channel, "message_template": template or "", "recipients": recipients or []
        })
        self.nodes[node.id] = node
        return self

    def add_exporter(self, format="markdown", path="./exports"):
        node = create_node(NodeType.EXPORT, "Exporter", {
            "format": format, "path": path, "include_content": True
        })
        self.nodes[node.id] = node
        return self

    def add_condition(self, expression):
        node = create_node(NodeType.CONDITION, "Condition", {
            "if_expression": expression
        })
        self.nodes[node.id] = node
        return self

    def add_transform(self, script):
        node = create_node(NodeType.TRANSFORM, "Transform", {
            "script": script
        })
        self.nodes[node.id] = node
        return self

    def add_delay(self, seconds):
        node = create_node(NodeType.DELAY, "Delay", {
            "seconds": seconds
        })
        self.nodes[node.id] = node
        return self

    def connect(self, from_id, to_id):
        self.edges.append({"from": from_id, "to": to_id, "label": ""})
        if from_id in self.nodes:
            self.nodes[from_id].next_nodes.append(to_id)
        return self

    def build(self):
        return {
            "id": str(uuid.uuid4()),
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": self.edges,
            "created_at": datetime.utcnow().isoformat(),
        }

    def save(self, path):
        workflow = self.build()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)

    def load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.name = data.get("name", self.name)
        self.description = data.get("description", self.description)
        self.nodes = {}
        for nd in data.get("nodes", []):
            self.nodes[nd["id"]] = WorkflowNode.from_dict(nd)
        self.edges = data.get("edges", [])
        return data

    def validate(self):
        errors = []
        visited = set()
        rec_stack = set()

        def has_cycle(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)
            for edge in self.edges:
                if edge["from"] == node_id:
                    if edge["to"] in rec_stack:
                        return True
                    if edge["to"] not in visited:
                        if has_cycle(edge["to"]):
                            return True
            rec_stack.discard(node_id)
            return False

        for nid in list(self.nodes.keys()):
            if nid not in visited:
                if has_cycle(nid):
                    errors.append("Cycle detected in workflow graph")
                    break

        connected = set()
        for edge in self.edges:
            connected.add(edge["from"])
            connected.add(edge["to"])
        for nid in self.nodes:
            if nid not in connected:
                has_incoming = any(e["to"] == nid for e in self.edges)
                has_outgoing = any(e["from"] == nid for e in self.edges)
                if not has_incoming and not has_outgoing and len(self.nodes) > 1:
                    errors.append(f"Node '{self.nodes[nid].name}' ({nid}) is completely disconnected")

        for nid, node in self.nodes.items():
            has_outgoing = any(e["from"] == nid for e in self.edges)
            if not has_outgoing and node.type not in (NodeType.END, NodeType.CONDITION):
                incoming = any(e["to"] == nid for e in self.edges)
                if incoming:
                    errors.append(f"Node '{node.name}' ({nid}) has no outgoing connections (dead end)")

        return errors

    def to_mermaid(self):
        lines = ["graph TD"]
        for nid, node in self.nodes.items():
            safe_name = node.name.replace('"', "#quot;")
            node_label = f"{safe_name}[{node.type.value}]"
            lines.append(f"    {nid}[\"{node_label}\"]")
        for edge in self.edges:
            label = edge.get("label", "")
            if label:
                lines.append(f"    {edge['from']} -- \"{label}\" --> {edge['to']}")
            else:
                lines.append(f"    {edge['from']} --> {edge['to']}")
        return "\n".join(lines)
