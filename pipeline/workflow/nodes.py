import uuid
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional
from pydantic import BaseModel, Field


class NodeType(Enum):
    TRIGGER = "trigger"
    COLLECT = "collect"
    FILTER = "filter"
    CLASSIFY = "classify"
    TRANSFORM = "transform"
    NOTIFY = "notify"
    EXPORT = "export"
    DELAY = "delay"
    CONDITION = "condition"
    MERGE = "merge"
    LOOP = "loop"
    END = "end"


@dataclass
class WorkflowNode:
    id: str
    type: NodeType
    name: str
    config: dict = field(default_factory=dict)
    position: tuple = (0, 0)
    next_nodes: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "config": self.config,
            "position": list(self.position),
            "next_nodes": self.next_nodes,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            name=data.get("name", ""),
            config=data.get("config", {}),
            position=tuple(data.get("position", [0, 0])),
            next_nodes=data.get("next_nodes", []),
        )


class TriggerConfig(BaseModel):
    schedule: str = ""
    source: str = ""
    topic: str = ""


class CollectConfig(BaseModel):
    source: str = ""
    max_items: int = 10
    query: str = ""


class FilterConfig(BaseModel):
    condition: str = ""
    min_relevance: float = 0.0
    topics: list[str] = Field(default_factory=list)


class ClassifyConfig(BaseModel):
    method: str = "keyword"
    topics: list[str] = Field(default_factory=list)


class NotifyConfig(BaseModel):
    channel: str = "slack"
    message_template: str = ""
    recipients: list[str] = Field(default_factory=list)


class ExportConfig(BaseModel):
    format: str = "markdown"
    path: str = "./exports"
    include_content: bool = True


class ConditionConfig(BaseModel):
    if_expression: str = ""
    true_node: str = ""
    false_node: str = ""


class TransformConfig(BaseModel):
    script: str = ""


CONFIG_MAP = {
    NodeType.TRIGGER: TriggerConfig,
    NodeType.COLLECT: CollectConfig,
    NodeType.FILTER: FilterConfig,
    NodeType.CLASSIFY: ClassifyConfig,
    NodeType.NOTIFY: NotifyConfig,
    NodeType.EXPORT: ExportConfig,
    NodeType.CONDITION: ConditionConfig,
    NodeType.TRANSFORM: TransformConfig,
}


def create_node(node_type: NodeType, name: str, config: dict) -> WorkflowNode:
    return WorkflowNode(
        id=str(uuid.uuid4()),
        type=node_type,
        name=name,
        config=config,
    )


def validate_node(node: WorkflowNode) -> tuple[bool, str]:
    model_class = CONFIG_MAP.get(node.type)
    if model_class is None:
        return True, "valid"
    try:
        model_class(**node.config)
        return True, "valid"
    except Exception as e:
        return False, str(e)
