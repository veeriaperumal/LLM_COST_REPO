# ---------------------------------------------------------------------------
# 2_live_router.py — Live Router dashboard page
# ---------------------------------------------------------------------------
# Interactive form to submit routing requests and visualize results.
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
from dashboard.styles import pipeline_steps


def render() -> None:
    st.title("Live Router")

    client = APIClient(st.session_state.get("api_base_url", "http://localhost:8000"))

    # -- Request form ---------------------------------------------------------
    with st.form("route_form"):
        st.subheader("Routing Request")

        col1, col2 = st.columns(2)
        with col1:
            task = st.selectbox(
                "Task Type",
                ["classification", "extraction", "summarisation", "qa"],
            )
            require_structured = st.checkbox("Require Structured Output")
            require_tools = st.checkbox("Require Tool Calling")
        with col2:
            prompt = st.text_area("Prompt", height=100, value="Classify this text as positive or negative.")
            max_cost = st.number_input("Max Cost (USD)", min_value=0.0, value=0.0, step=0.001, format="%.4f")
            max_cost_val = max_cost if max_cost > 0 else None

        run_graph = st.checkbox("Run full LangGraph workflow", value=False)

        submitted = st.form_submit_button("Route", type="primary")

    # -- Execute routing ------------------------------------------------------
    if submitted:
        payload = {
            "task": task,
            "prompt": prompt,
            "estimated_output_tokens": 256,
            "require_structured_output": require_structured,
            "require_tools": require_tools,
            "max_cost_usd": max_cost_val,
        }

        with st.spinner("Routing request..."):
            if run_graph:
                result = asyncio.run(client.route_graph(payload))
            else:
                result = asyncio.run(client.route_request(payload))

        if result is None:
            st.error("Could not reach the API server. Make sure it is running on http://localhost:8000")
            return

        st.success("Routing complete!")

        # -- Display result ---------------------------------------------------
        if run_graph:
            _display_graph_result(result)
        else:
            _display_routing_result(result)


def _display_routing_result(result: dict) -> None:
    """Display a RoutingResult from POST /api/v1/route."""
    selected = result.get("selected_model")
    scores = result.get("scores", {})

    # Selected model
    st.subheader("Selected Model")
    if selected:
        st.success(f"**{selected}**")
    else:
        st.warning("No model selected")

    # Pipeline
    st.subheader("Routing Pipeline")
    all_candidates = result.get("all_candidates", [])
    eligible = result.get("eligible", [])
    pareto = result.get("pareto_frontier", [])
    excluded = [e.get("model_id", "") for e in result.get("exclusions", [])]

    steps_html = pipeline_steps(
        ["candidates", "capability", "constraint", "pareto", "score", "select"],
        completed=[
            "candidates",
            "capability" if eligible else "",
            "constraint" if eligible else "",
            "pareto" if pareto else "",
            "score" if scores else "",
            "select" if selected else "",
        ],
    )
    st.markdown(steps_html, unsafe_allow_html=True)

    # Score breakdown chart
    if scores:
        st.subheader("Score Breakdown")
        model_ids = list(scores.keys())
        qualities = [s.get("quality", 0) for s in scores.values()]
        latency_scores = [s.get("latency_score", 0) for s in scores.values()]
        cost_scores = [s.get("cost_score", 0) for s in scores.values()]
        total_scores = [s.get("score", 0) for s in scores.values()]

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Quality (0.45)", x=model_ids, y=qualities, marker_color="#3b82f6"))
        fig.add_trace(go.Bar(name="Latency (0.30)", x=model_ids, y=latency_scores, marker_color="#22c55e"))
        fig.add_trace(go.Bar(name="Cost (0.25)", x=model_ids, y=cost_scores, marker_color="#f59e0b"))
        fig.add_trace(go.Bar(name="Total Score", x=model_ids, y=total_scores, marker_color="#8b5cf6"))
        fig.update_layout(barmode="group", margin=dict(t=20, b=20), height=350)
        st.plotly_chart(fig, width="stretch")

    # Exclusions table
    exclusions = result.get("exclusions", [])
    if exclusions:
        st.subheader("Excluded Models")
        st.dataframe(
            [{"Model": e.get("model_id"), "Stage": e.get("stage"), "Reason": e.get("reason")} for e in exclusions],
            width="stretch",
        )


def _display_graph_result(result: dict) -> None:
    """Display a graph workflow result from POST /api/v1/route/graph."""
    selected = result.get("selected_model")
    evaluation = result.get("evaluation", {})
    stages = result.get("stages_completed", [])

    # Selected model + evaluation
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Selected Model")
        if selected:
            st.success(f"**{selected}**")
        else:
            st.warning("No model selected")

    with col2:
        st.subheader("Evaluation")
        status = evaluation.get("status", "unknown")
        score = evaluation.get("score", 0)
        st.metric("Score", f"{score:.2f}")
        st.markdown(f"**Status:** {status}")
        if evaluation.get("reason"):
            st.caption(evaluation["reason"])

    # Pipeline stages
    st.subheader("Workflow Stages")
    all_stages = ["analyze", "filter", "route", "execute", "evaluate", "finalize"]
    steps_html = pipeline_steps(all_stages, completed=stages)
    st.markdown(steps_html, unsafe_allow_html=True)

    # Response content
    content = result.get("response_content")
    if content:
        st.subheader("Response")
        st.text_area("Model Output", content, height=150, disabled=True)

    # Cost + retries
    col3, col4, col5 = st.columns(3)
    with col3:
        st.metric("Cost", f"${result.get('cost_usd', 0):.4f}")
    with col4:
        st.metric("Retries", result.get("retry_count", 0))
    with col5:
        routing_summary = result.get("routing_summary", {})
        st.metric("Candidates", len(routing_summary.get("all_candidates", [])))
