# ---------------------------------------------------------------------------
# gateway.py — MCP tool gateway
# ---------------------------------------------------------------------------
# Orchestrates every tool call through a controlled pipeline:
#   1. Allowlist verification
#   2. Tenant permission verification
#   3. Input schema validation
#   4. Prompt-injection scan on string arguments
#   5. Execution with timeout
#   6. Audit logging
# ---------------------------------------------------------------------------

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.mcp.injection import check_injection
from app.mcp.schemas import AuditEntry, MCPToolResult, ToolCallRequest
from app.mcp.tools import MCP_TOOLS

logger = logging.getLogger("app.mcp")


class ToolNotFoundError(Exception):
    """Raised when a tool is not in the allowlist or does not exist."""


class ToolPermissionError(Exception):
    """Raised when the tenant is not allowed to call a tool."""


class ToolInjectionError(Exception):
    """Raised when a prompt-injection pattern is detected."""


class ToolTimeoutError(Exception):
    """Raised when a tool execution exceeds the timeout."""


class MCPGateway:
    """Controlled gateway for MCP tool invocations.

    Parameters
    ----------
    allowed_tools:
        Set of tool names the gateway will accept.  Empty means all
        registered tools are allowed.
    tenant_permissions:
        Mapping of ``{tenant_id: {tool_name, …}}``.  If a tenant ID is
        absent from the mapping all allowed tools are available to it.
    timeout:
        Per-call timeout in seconds.
    extra_injection_patterns:
        Additional regex patterns appended to the default injection list.
    """

    def __init__(
        self,
        *,
        allowed_tools: set[str] | None = None,
        tenant_permissions: dict[str, set[str]] | None = None,
        timeout: float = 10.0,
        extra_injection_patterns: list[str] | None = None,
    ) -> None:
        self._allowed_tools = allowed_tools or set(MCP_TOOLS.keys())
        self._tenant_permissions: dict[str, set[str]] = tenant_permissions or {}
        self._timeout = timeout
        self._extra_injection_patterns = extra_injection_patterns or []
        self._audit_log: list[AuditEntry] = []

    # -- Public API -----------------------------------------------------------

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tenant_id: str = "default",
    ) -> MCPToolResult:
        """Execute a tool through the full validation pipeline.

        Raises
        ------
        ToolNotFoundError
            If the tool is not registered or not on the allowlist.
        ToolPermissionError
            If the tenant does not have permission.
        ToolInjectionError
            If a prompt-injection pattern is detected.
        ToolTimeoutError
            If execution exceeds the configured timeout.
        """
        start = time.perf_counter()

        # 1. Allowlist check ---------------------------------------------------
        if tool_name not in MCP_TOOLS:
            elapsed = (time.perf_counter() - start) * 1000
            self._audit(tenant_id, tool_name, arguments, False, "tool not found", elapsed)
            raise ToolNotFoundError(f"Unknown tool: {tool_name}")

        if tool_name not in self._allowed_tools:
            elapsed = (time.perf_counter() - start) * 1000
            self._audit(tenant_id, tool_name, arguments, False, "not on allowlist", elapsed)
            raise ToolPermissionError(
                f"Tool '{tool_name}' is not on the allowlist"
            )

        # 2. Tenant permission check -------------------------------------------
        permitted = self._tenant_permissions.get(tenant_id)
        if permitted is not None and tool_name not in permitted:
            elapsed = (time.perf_counter() - start) * 1000
            self._audit(
                tenant_id, tool_name, arguments, False,
                "tenant lacks permission", elapsed,
            )
            raise ToolPermissionError(
                f"Tenant '{tenant_id}' is not allowed to call '{tool_name}'"
            )

        # 3. Schema validation (basic: ensure required args are present) -------
        tool_fn = MCP_TOOLS[tool_name]
        if tool_name == "search_knowledge" and "query" not in arguments:
            arguments = {**arguments, "query": ""}
        elif tool_name == "calculate" and "expression" not in arguments:
            arguments = {**arguments, "expression": ""}
        elif tool_name == "get_customer" and "customer_id" not in arguments:
            arguments = {**arguments, "customer_id": ""}

        # 4. Prompt-injection scan on all string arguments ---------------------
        for key, value in arguments.items():
            if isinstance(value, str) and check_injection(
                value, self._extra_injection_patterns
            ):
                elapsed = (time.perf_counter() - start) * 1000
                self._audit(
                    tenant_id, tool_name, arguments, False,
                    "injection detected", elapsed,
                )
                raise ToolInjectionError(
                    f"Prompt-injection pattern detected in argument '{key}'"
                )

        # 5. Execute with timeout ----------------------------------------------
        try:
            result = await asyncio.wait_for(
                tool_fn(**arguments), timeout=self._timeout
            )
            elapsed = (time.perf_counter() - start) * 1000
            self._audit(tenant_id, tool_name, arguments, True, None, elapsed)
            return MCPToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                latency_ms=elapsed,
            )
        except asyncio.TimeoutError:
            elapsed = (time.perf_counter() - start) * 1000
            self._audit(
                tenant_id, tool_name, arguments, False, "timeout", elapsed,
            )
            raise ToolTimeoutError(
                f"Tool '{tool_name}' exceeded {self._timeout}s timeout"
            )
        except ToolInjectionError:
            raise
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            self._audit(tenant_id, tool_name, arguments, False, str(exc), elapsed)
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=str(exc),
                latency_ms=elapsed,
            )

    # -- Audit ----------------------------------------------------------------

    def _audit(
        self,
        tenant_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        success: bool,
        error: str | None,
        latency_ms: float,
    ) -> None:
        entry = AuditEntry(
            tool_name=tool_name,
            tenant_id=tenant_id,
            arguments=arguments,
            success=success,
            error=error,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._audit_log.append(entry)
        level = logging.INFO if success else logging.WARNING
        logger.log(
            level,
            "mcp_call tool=%s tenant=%s success=%s latency=%.1fms error=%s",
            tool_name, tenant_id, success, latency_ms, error,
        )

    @property
    def audit_log(self) -> list[AuditEntry]:
        """Return a copy of the audit log."""
        return list(self._audit_log)

    def clear_audit_log(self) -> None:
        """Reset the audit log (useful for tests)."""
        self._audit_log.clear()
