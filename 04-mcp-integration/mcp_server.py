"""
MCP (Model Context Protocol) server — the action layer for agents.
Enables Claude, OpenAI, Copilot to connect directly into your systems.
"""

import json
from typing import Any
from pydantic import BaseModel

class MCPRequest(BaseModel):
    tool: str
    params: dict[str, Any]
    user_id: str

class MCPResponse(BaseModel):
    success: bool
    data: Any
    error: str | None = None

class MCPServer:
    def __init__(self):
        self._tools: dict[str, callable] = {}
        self._rbac: dict[str, list[str]] = {}

    def register_tool(self, name: str, handler: callable,
                      required_roles: list[str] | None = None):
        self._tools[name] = handler
        self._rbac[name] = required_roles or ["user"]

    def execute(self, request: MCPRequest) -> MCPResponse:
        if request.tool not in self._tools:
            return MCPResponse(success=False, error="Tool not found")
        try:
            result = self._tools[request.tool](**request.params)
            return MCPResponse(success=True, data=result)
        except Exception as e:
            return MCPResponse(success=False, error=str(e))

mcp = MCPServer()

@mcp.register_tool("read_file", required_roles=["user", "admin"])
def read_file(path: str):
    with open(path, "r") as f:
        return f.read()

@mcp.register_tool("search_database", required_roles=["admin"])
def search_database(query: str):
    return {"result": f"Simulated: {query}"}

request = MCPRequest(tool="read_file", params={"path": "test.txt"}, user_id="user1")
response = mcp.execute(request)
print(response.model_dump_json(indent=2))
