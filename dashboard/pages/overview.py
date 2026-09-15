# ---------------------------------------------------------------------------
# 1_overview.py — Overview dashboard page
# ---------------------------------------------------------------------------
# Displays aggregate KPIs, model usage, routing decisions, and latency.
# ---------------------------------------------------------------------------

import os
import sys

_root = os.getcwd()
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from dashboard.api_client import APIClient
from dashboard.mock_data import (
    MOCK_HEALTH,
    MOCK_LATENCY_DISTRIBUTION,
    MOCK_MODEL_USAGE,
    MOCK_ROUTING_DECISIONS,
)
from dashboard.styles import kpi_card, status_badge


def render() -> None:
    st.title("Overview")

    client = APIClient(st.session_state.get("api_base_url", "http://localhost:8000"))

    # -- Row 1: KPI cards -----------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    total_requests = sum(MOCK_ROUTING_DECISIONS.values())
    accept_rate = MOCK_ROUTING_DECISIONS["accept"] / total_requests * 100
    avg_cost = 0.0023
    savings = 34.0

    with col1:
        kpi_card("Total Requests", f"{total_requests:,}")
    with col2:
        kpi_card("Avg Cost / Request", f"${avg_cost:.4f}")
    with col3:
        kpi_card("Cost Savings", f"{savings:.0f}%", delta="vs strongest baseline")
    with col4:
        kpi_card("Accept Rate", f"{accept_rate:.0f}%")

    st.markdown("---")

    # -- Row 2: Model usage + Routing decisions -------------------------------
    left, right = st.columns(2)

    with left:
        st.subheader("Model Usage Distribution")
        fig_usage = px.pie(
            names=list(MOCK_MODEL_USAGE.keys()),
            values=list(MOCK_MODEL_USAGE.values()),
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig_usage.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
        st.plotly_chart(fig_usage, width="stretch")

    with right:
        st.subheader("Routing Decisions")
        fig_decisions = px.bar(
            x=list(MOCK_ROUTING_DECISIONS.keys()),
            y=list(MOCK_ROUTING_DECISIONS.values()),
            color=list(MOCK_ROUTING_DECISIONS.keys()),
            color_discrete_map={"accept": "#22c55e", "revise": "#f59e0b", "escalate": "#ef4444"},
        )
        fig_decisions.update_layout(
            xaxis_title="Decision",
            yaxis_title="Count",
            showlegend=False,
            margin=dict(t=20, b=20),
            height=300,
        )
        st.plotly_chart(fig_decisions, width="stretch")

    # -- Row 3: Latency percentiles + Provider health ------------------------
    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Latency Distribution")
        lat_data = MOCK_LATENCY_DISTRIBUTION
        fig_latency = go.Figure(
            go.Bar(
                x=list(lat_data.keys()),
                y=list(lat_data.values()),
                marker_color=["#3b82f6", "#f59e0b", "#ef4444", "#22c55e", "#6b728b"],
                text=[f"{v:.0f}ms" for v in lat_data.values()],
                textposition="outside",
            )
        )
        fig_latency.update_layout(
            xaxis_title="Percentile",
            yaxis_title="Latency (ms)",
            margin=dict(t=20, b=20),
            height=300,
        )
        st.plotly_chart(fig_latency, width="stretch")

    with right2:
        st.subheader("Service Health")

        # Try live health first
        import asyncio

        health = None
        try:
            health = asyncio.run(client.get_health())
        except Exception:
            pass

        health = health or MOCK_HEALTH

        for svc, info in health.get("services", {}).items():
            status = info.get("status", "unknown")
            st.markdown(
                f"**{svc.title()}** {status_badge(status)}",
                unsafe_allow_html=True,
            )
            if info.get("message"):
                st.caption(info["message"])
