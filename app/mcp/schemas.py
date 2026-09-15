# ---------------------------------------------------------------------------
# schemas.py — Pydantic models for MCP tool definitions and results
# ---------------------------------------------------------------------------
# Defines the data shapes flowing through the MCP gateway: tool definitions,
# tool call requests, and tool call results.
# ---------------------------------------------------------------------------

from typing import Any

from pydantic import BaseModel, Field


class MCPToolDefinition(BaseModel):
    """Describes a single MCP tool available to the gateway."""

    name: str = Field(..., description="Unique tool name, e.g. 'search_knowledge'")
    description: str = Field(..., description="Human-readable purpose of the tool")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON-Schema-style parameter definition",
    )


class MCPToolResult(BaseModel):
    """Structured result returned by every tool invocation."""

    tool_name: str
    success: bool
    result: Any | None = None
    error: str | None = None
    latency_ms: float = 0.0


class ToolCallRequest(BaseModel):
    """Incoming tool call from the graph or API layer."""

    tool_name: str = Field(..., description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = Field(default="default", description="Caller's tenant identifier")


class AuditEntry(BaseModel):
    """Immutable record of a single tool invocation."""

    tool_name: str
    tenant_id: str
    arguments: dict[str, Any]
    success: bool
    error: str | None = None
    latency_ms: float = 0.0
    timestamp: str = ""
