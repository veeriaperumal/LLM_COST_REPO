# ---------------------------------------------------------------------------
# 6_observability.py — Observability dashboard page
# ---------------------------------------------------------------------------
# Service health, MCP audit log, graph workflow trace, and error tracking.
# ---------------------------------------------------------------------------

import asyncio
import os
import sys

_root = os.getcwd()
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.graph_objects as go

from dashboard.api_client import APIClient
from dashboard.mock_data import MOCK_AUDIT_ENTRIES, MOCK_HEALTH
from dashboard.styles import status_badge


def render() -> None:
    st.title("Observability")

    client = APIClient(st.session_state.get("api_base_url", "http://localhost:8000"))

    # -- Service health -------------------------------------------------------
    st.subheader("Service Health")

    health = None
    try:
        health = asyncio.run(client.get_health())
    except Exception:
        pass
    health = health or MOCK_HEALTH

    cols = st.columns(len(health.get("services", {})))
    for i, (svc, info) in enumerate(health.get("services", {}).items()):
        with cols[i]:
            status = info.get("status", "unknown")
            st.markdown(
                f"**{svc.title()}**<br>{status_badge(status)}",
                unsafe_allow_html=True,
            )
            if info.get("message"):
                st.caption(info["message"])

    st.markdown("---")

    # -- MCP Audit Log --------------------------------------------------------
    st.subheader("MCP Tool Audit Log")

    audit = MOCK_AUDIT_ENTRIES

    # Filter
    col1, col2 = st.columns(2)
    with col1:
        tool_filter = st.multiselect(
            "Tool",
            options=["search_knowledge", "calculate", "get_customer"],
            default=["search_knowledge", "calculate", "get_customer"],
            key="audit_tool_filter",
        )
    with col2:
        status_filter = st.multiselect(
            "Status",
            options=["success", "failure"],
            default=["success", "failure"],
            key="audit_status_filter",
        )

    filtered_audit = [
        e for e in audit
        if e["tool_name"] in tool_filter
        and (("success" if e["success"] else "failure") in status_filter)
    ]

    if filtered_audit:
        audit_table = [
            {
                "Time": e["timestamp"][:19],
                "Tool": e["tool_name"],
                "Tenant": e["tenant_id"],
                "Status": "ok" if e["success"] else "down",
                "Latency": f"{e['latency_ms']:.1f}ms",
                "Error": e.get("error", ""),
            }
            for e in filtered_audit[:20]
        ]
        st.dataframe(audit_table, width="stretch", height=300)
    else:
        st.info("No audit entries match the filters.")

    # -- Audit stats ----------------------------------------------------------
    st.markdown("---")
    st.subheader("Tool Usage Stats")

    total_calls = len(audit)
    success_calls = sum(1 for e in audit if e["success"])
    failed_calls = total_calls - success_calls
    avg_latency = sum(e["latency_ms"] for e in audit) / max(total_calls, 1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Calls", total_calls)
    with col2:
        st.metric("Successful", success_calls)
    with col3:
        st.metric("Failed", failed_calls)
    with col4:
        st.metric("Avg Latency", f"{avg_latency:.1f}ms")

    # Tool distribution chart
    tool_counts = {}
    for e in audit:
        tool_counts[e["tool_name"]] = tool_counts.get(e["tool_name"], 0) + 1

    fig_tool = go.Figure(go.Bar(
        x=list(tool_counts.keys()),
        y=list(tool_counts.values()),
        marker_color="#3b82f6",
    ))
    fig_tool.update_layout(
        xaxis_title="Tool",
        yaxis_title="Calls",
        margin=dict(t=20, b=20),
        height=250,
    )
    st.plotly_chart(fig_tool, width="stretch")

    st.markdown("---")

    # -- Graph Workflow Trace -------------------------------------------------
    st.subheader("Graph Workflow Trace")

    st.caption("Latest workflow executions from the LangGraph state machine")

    mock_traces = [
        {
            "request_id": "req-0012",
            "stages": ["analyze", "filter", "route", "execute", "evaluate", "finalize"],
            "selected_model": "gpt-4o-mini",
            "evaluation_status": "accept",
            "evaluation_score": 0.9,
            "cost_usd": 0.0008,
        },
        {
            "request_id": "req-0011",
            "stages": ["analyze", "filter", "route", "execute", "evaluate", "route", "execute", "evaluate", "finalize"],
            "selected_model": "claude-3-5-sonnet",
            "evaluation_status": "revise",
            "evaluation_score": 0.7,
            "cost_usd": 0.0045,
        },
        {
            "request_id": "req-0010",
            "stages": ["analyze", "filter", "finalize"],
            "selected_model": None,
            "evaluation_status": "escalate",
            "evaluation_score": 0.0,
            "cost_usd": 0.0,
        },
    ]

    for trace in mock_traces:
        with st.expander(f"**{trace['request_id']}** — {trace['selected_model'] or 'no model'} ({trace['evaluation_status']})", expanded=False):
            from dashboard.styles import pipeline_steps
            st.markdown(
                pipeline_steps(
                    ["analyze", "filter", "route", "execute", "evaluate", "finalize"],
                    completed=trace["stages"],
                ),
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{trace['evaluation_score']:.2f}")
            with col2:
                st.metric("Cost", f"${trace['cost_usd']:.4f}")
            with col3:
                st.metric("Steps", len(trace["stages"]))

    st.markdown("---")

    # -- Error rate -----------------------------------------------------------
    st.subheader("Error Tracking")

    mock_errors = [
        {"type": "RoutingError", "count": 5, "last_seen": "2h ago"},
        {"type": "ProviderTimeout", "count": 2, "last_seen": "45m ago"},
        {"type": "ToolInjectionBlocked", "count": 8, "last_seen": "10m ago"},
        {"type": "BudgetExceeded", "count": 3, "last_seen": "1h ago"},
    ]

    fig_errors = go.Figure(go.Bar(
        x=[e["type"] for e in mock_errors],
        y=[e["count"] for e in mock_errors],
        marker_color="#ef4444",
        text=[e["last_seen"] for e in mock_errors],
        textposition="outside",
    ))
    fig_errors.update_layout(
        xaxis_title="Error Type",
        yaxis_title="Count",
        margin=dict(t=20, b=20),
        height=250,
    )
    st.plotly_chart(fig_errors, width="stretch")
