"""MCP (Model Context Protocol) server for AI Content Hub.

Exposes content sources, search, and project data as MCP resources
so AI agents can query content hub data directly.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    import mcp.types as types

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class ContentHubMCP:
    """Exposes AI Content Hub data via Model Context Protocol."""

    def __init__(self, sql_store=None, vector_store=None):
        self.sql_store = sql_store
        self.vector_store = vector_store
        self.server = None
        self._resources = {}
        self._tools = {}

    def is_available(self) -> bool:
        return MCP_AVAILABLE

    def _build_resources(self):
        self._resources = {
            "content://stats": types.Resource(
                uri="content://stats",
                name="Content Hub Stats",
                description="Aggregate statistics across all content sources",
                mimeType="application/json",
            ),
            "content://topics": types.Resource(
                uri="content://topics",
                name="All Topics",
                description="List of all tracked topics with item counts",
                mimeType="application/json",
            ),
            "content://sources": types.Resource(
                uri="content://sources",
                name="All Sources",
                description="List of all content sources with item counts",
                mimeType="application/json",
            ),
        }

    def _build_tools(self):
        self._tools = {
            "search_content": types.Tool(
                name="search_content",
                description="Search across all content items by query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results", "default": 20},
                        "topic": {"type": "string", "description": "Filter by topic"},
                        "source": {"type": "string", "description": "Filter by source"},
                    },
                    "required": ["query"],
                },
            ),
            "get_recent_content": types.Tool(
                name="get_recent_content",
                description="Get the most recent content items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of items", "default": 20},
                        "topic": {"type": "string", "description": "Filter by topic"},
                        "source": {"type": "string", "description": "Filter by source"},
                    },
                },
            ),
            "get_content_by_topic": types.Tool(
                name="get_content_by_topic",
                description="Get content items filtered by topic",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Topic name"},
                        "limit": {"type": "integer", "description": "Max results", "default": 20},
                    },
                    "required": ["topic"],
                },
            ),
            "get_content_by_source": types.Tool(
                name="get_content_by_source",
                description="Get content items filtered by source",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source name"},
                        "limit": {"type": "integer", "description": "Max results", "default": 20},
                    },
                    "required": ["source"],
                },
            ),
            "get_model_list": types.Tool(
                name="get_model_list",
                description="List available AI models by tier",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tier": {"type": "string", "description": "Filter by tier: free, premium, or all"},
                    },
                },
            ),
        }

    async def _handle_list_resources(self) -> list[types.Resource]:
        return list(self._resources.values())

    async def _handle_read_resource(self, uri: str) -> str:
        if uri == "content://stats":
            return json.dumps(self._get_stats(), indent=2)
        elif uri == "content://topics":
            return json.dumps(self._get_topics(), indent=2)
        elif uri == "content://sources":
            return json.dumps(self._get_sources(), indent=2)
        raise ValueError(f"Unknown resource: {uri}")

    async def _handle_list_tools(self) -> list[types.Tool]:
        return list(self._tools.values())

    async def _handle_call_tool(self, name: str, arguments: dict) -> list[types.TextContent]:
        if name == "search_content":
            results = self._search(arguments.get("query", ""), arguments.get("limit", 20), arguments.get("topic"), arguments.get("source"))
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
        elif name == "get_recent_content":
            results = self._get_recent(arguments.get("limit", 20), arguments.get("topic"), arguments.get("source"))
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
        elif name == "get_content_by_topic":
            results = self._get_by_topic(arguments.get("topic", ""), arguments.get("limit", 20))
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
        elif name == "get_content_by_source":
            results = self._get_by_source(arguments.get("source", ""), arguments.get("limit", 20))
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
        elif name == "get_model_list":
            results = self._get_models(arguments.get("tier", "all"))
            return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
        raise ValueError(f"Unknown tool: {name}")

    def _get_stats(self) -> dict:
        if self.sql_store:
            try:
                items = self.sql_store.get_all()
                by_source = {}
                by_topic = {}
                for item in items:
                    by_source[item.source] = by_source.get(item.source, 0) + 1
                    for topic in item.topics:
                        by_topic[topic] = by_topic.get(topic, 0) + 1
                return {"total_items": len(items), "by_source": by_source, "by_topic": by_topic}
            except Exception as e:
                logger.warning(f"MCP stats error: {e}")
        return {"total_items": 0, "by_source": {}, "by_topic": {}}

    def _get_topics(self) -> list[dict]:
        if self.sql_store:
            try:
                items = self.sql_store.get_all()
                topic_counts = {}
                for item in items:
                    for topic in item.topics:
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1
                return [{"topic": k, "count": v} for k, v in sorted(topic_counts.items(), key=lambda x: -x[1])]
            except Exception as e:
                logger.warning(f"MCP topics error: {e}")
        return []

    def _get_sources(self) -> list[dict]:
        if self.sql_store:
            try:
                items = self.sql_store.get_all()
                source_counts = {}
                for item in items:
                    source_counts[item.source] = source_counts.get(item.source, 0) + 1
                return [{"source": k, "count": v} for k, v in sorted(source_counts.items(), key=lambda x: -x[1])]
            except Exception as e:
                logger.warning(f"MCP sources error: {e}")
        return []

    def _search(self, query: str, limit: int = 20, topic: str | None = None, source: str | None = None) -> list[dict]:
        if self.sql_store:
            try:
                items = self.sql_store.search(query, limit=limit * 3)
                results = []
                for item in items:
                    if topic and topic not in item.topics:
                        continue
                    if source and item.source != source:
                        continue
                    results.append(item.model_dump())
                    if len(results) >= limit:
                        break
                return results
            except Exception as e:
                logger.warning(f"MCP search error: {e}")
        return []

    def _get_recent(self, limit: int = 20, topic: str | None = None, source: str | None = None) -> list[dict]:
        if self.sql_store:
            try:
                items = self.sql_store.get_recent(limit=limit * 3)
                results = []
                for item in items:
                    if topic and topic not in item.topics:
                        continue
                    if source and item.source != source:
                        continue
                    results.append(item.model_dump())
                    if len(results) >= limit:
                        break
                return results
            except Exception as e:
                logger.warning(f"MCP recent error: {e}")
        return []

    def _get_by_topic(self, topic: str, limit: int = 20) -> list[dict]:
        if self.sql_store:
            try:
                items = self.sql_store.get_by_topic(topic, limit=limit)
                return [item.model_dump() for item in items]
            except Exception as e:
                logger.warning(f"MCP topic error: {e}")
        return []

    def _get_by_source(self, source: str, limit: int = 20) -> list[dict]:
        if self.sql_store:
            try:
                items = self.sql_store.get_by_source(source, limit=limit)
                return [item.model_dump() for item in items]
            except Exception as e:
                logger.warning(f"MCP source error: {e}")
        return []

    def _get_models(self, tier: str = "all") -> list[dict]:
        try:
            from ..ai.model_registry import get_model_registry

            registry = get_model_registry()
            models = registry.list_models()
            if tier != "all":
                models = [m for m in models if m.tier == tier]
            return [m.model_dump() for m in models]
        except Exception as e:
            logger.warning(f"MCP models error: {e}")
        return []

    async def run(self):
        if not MCP_AVAILABLE:
            logger.warning("MCP SDK not installed. Install with: pip install mcp")
            return

        self._build_resources()
        self._build_tools()

        self.server = Server("ai-content-hub")

        self.server.list_resources = self._handle_list_resources
        self.server.read_resource = self._handle_read_resource
        self.server.list_tools = self._handle_list_tools
        self.server.call_tool = self._handle_call_tool

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ai-content-hub",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


if __name__ == "__main__":
    import asyncio
    mcp_server = ContentHubMCP()
    asyncio.run(mcp_server.run())
