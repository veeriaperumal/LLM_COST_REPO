# ---------------------------------------------------------------------------
# 3_request_explorer.py — Request Explorer dashboard page
# ---------------------------------------------------------------------------
# Browse and inspect routing decisions.  Uses mock data until Phase 2
# (PostgreSQL) is implemented for persistent request storage.
# ---------------------------------------------------------------------------

import os
import sys

_root = os.getcwd()
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.graph_objects as go

from dashboard.mock_data import MOCK_REQUEST_HISTORY
from dashboard.styles import status_badge


def render() -> None:
    st.title("Request Explorer")
    st.info("Showing demo data. Real request history requires Phase 2 (PostgreSQL).")

    history = MOCK_REQUEST_HISTORY

    # -- Filters --------------------------------------------------------------
    st.subheader("Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        task_filter = st.multiselect(
            "Task Type",
            options=["classification", "extraction", "summarisation", "qa"],
            default=["classification", "extraction", "summarisation", "qa"],
        )
    with col2:
        model_filter = st.multiselect(
            "Model",
            options=["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-haiku-4-5"],
            default=["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-haiku-4-5"],
        )
    with col3:
        status_filter = st.multiselect(
            "Status",
            options=["accept", "revise", "escalate"],
            default=["accept", "revise", "escalate"],
        )

    # Apply filters
    filtered = [
        r for r in history
        if r["task"] in task_filter
        and r["selected_model"] in model_filter
        and r["status"] in status_filter
    ]

    st.caption(f"Showing {len(filtered)} of {len(history)} requests")

    # -- Request table --------------------------------------------------------
    if not filtered:
        st.warning("No requests match the filters.")
        return

    table_data = [
        {
            "ID": r["request_id"],
            "Time": r["timestamp"][:16],
            "Task": r["task"],
            "Model": r["selected_model"],
            "Status": r["status"],
            "Score": r["evaluation_score"],
            "Cost": f"${r['cost_usd']:.4f}",
            "Latency": f"{r['latency_ms']:.0f}ms",
        }
        for r in filtered
    ]

    st.dataframe(table_data, width="stretch", height=300)

    # -- Detail view ----------------------------------------------------------
    st.markdown("---")
    st.subheader("Request Detail")

    request_ids = [r["request_id"] for r in filtered]
    selected_id = st.selectbox("Select a request", request_ids)

    detail = next((r for r in filtered if r["request_id"] == selected_id), None)
    if detail:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Prompt:** {detail['prompt']}")
            st.markdown(f"**Task:** {detail['task']}")
            st.markdown(f"**Model:** {detail['selected_model']} ({detail['provider']})")
            st.markdown(f"**Input Tokens:** {detail['input_tokens']}")

        with col2:
            st.markdown(f"**Status:** {status_badge(detail['status'])}", unsafe_allow_html=True)
            st.metric("Evaluation Score", f"{detail['evaluation_score']:.2f}")
            st.metric("Cost", f"${detail['cost_usd']:.4f}")
            st.metric("Latency", f"{detail['latency_ms']:.0f}ms")

        # Stages completed
        st.markdown("**Stages Completed:**")
        from dashboard.styles import pipeline_steps
        all_stages = ["analyze", "filter", "route", "execute", "evaluate", "finalize"]
        st.markdown(pipeline_steps(all_stages, completed=detail["stages_completed"]), unsafe_allow_html=True)

        # Cost vs latency scatter for all filtered requests
        st.markdown("---")
        st.subheader("Cost vs Latency")

        fig = go.Figure()
        for model in set(r["selected_model"] for r in filtered):
            model_data = [r for r in filtered if r["selected_model"] == model]
            fig.add_trace(go.Scatter(
                x=[r["latency_ms"] for r in model_data],
                y=[r["cost_usd"] for r in model_data],
                mode="markers",
                name=model,
                marker=dict(size=10),
            ))
        fig.update_layout(
            xaxis_title="Latency (ms)",
            yaxis_title="Cost (USD)",
            margin=dict(t=20, b=20),
            height=350,
        )
        st.plotly_chart(fig, width="stretch")
