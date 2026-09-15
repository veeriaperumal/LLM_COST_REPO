# ---------------------------------------------------------------------------
# 4_model_comparison.py — Model Comparison dashboard page
# ---------------------------------------------------------------------------
# Side-by-side model analysis with radar charts, pricing, and capabilities.
# ---------------------------------------------------------------------------

import asyncio
import os
import sys

_root = os.getcwd()
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from dashboard.api_client import APIClient
from dashboard.mock_data import MOCK_MODELS


def render() -> None:
    st.title("Model Comparison")

    client = APIClient(st.session_state.get("api_base_url", "http://localhost:8000"))

    # Fetch models from API or use mock
    models = None
    try:
        models = asyncio.run(client.get_models())
    except Exception:
        pass
    models = models or MOCK_MODELS

    model_ids = [m["model_id"] for m in models]

    # -- Model selector -------------------------------------------------------
    selected_ids = st.multiselect(
        "Select models to compare (2+)",
        options=model_ids,
        default=model_ids[:2],
    )

    if len(selected_ids) < 2:
        st.info("Select at least 2 models to compare.")
        return

    selected_models = [m for m in models if m["model_id"] in selected_ids]

    # -- Capability matrix ----------------------------------------------------
    st.subheader("Capabilities")

    cap_data = []
    for m in selected_models:
        caps = m["capabilities"]
        tasks = ", ".join(caps["supported_tasks"])
        cap_data.append({
            "Model": m["model_id"],
            "Provider": m["provider"],
            "Tasks": tasks,
            "Structured Output": "Yes" if caps["supports_structured_output"] else "No",
            "Tools": "Yes" if caps["supports_tools"] else "No",
            "Context": f"{caps['max_context_tokens']:,} tokens",
        })
    st.dataframe(cap_data, width="stretch")

    # -- Pricing comparison ---------------------------------------------------
    st.subheader("Pricing (per 1K tokens)")

    pricing_data = {
        "Model": [m["model_id"] for m in selected_models],
        "Input $/1K": [m["pricing"]["input_per_1k"] for m in selected_models],
        "Output $/1K": [m["pricing"]["output_per_1k"] for m in selected_models],
    }

    fig_pricing = go.Figure()
    fig_pricing.add_trace(go.Bar(
        name="Input",
        x=pricing_data["Model"],
        y=pricing_data["Input $/1K"],
        marker_color="#3b82f6",
    ))
    fig_pricing.add_trace(go.Bar(
        name="Output",
        x=pricing_data["Model"],
        y=pricing_data["Output $/1K"],
        marker_color="#8b5cf6",
    ))
    fig_pricing.update_layout(
        barmode="group",
        yaxis_title="USD per 1K tokens",
        margin=dict(t=20, b=20),
        height=350,
    )
    st.plotly_chart(fig_pricing, width="stretch")

    # -- Latency comparison ---------------------------------------------------
    st.subheader("Typical Latency")

    fig_latency = go.Figure(go.Bar(
        x=[m["model_id"] for m in selected_models],
        y=[m["typical_latency_ms"] for m in selected_models],
        marker_color=["#10a37f" if m["provider"] == "openai" else "#d97706" for m in selected_models],
        text=[f"{m['typical_latency_ms']:.0f}ms" for m in selected_models],
        textposition="outside",
    ))
    fig_latency.update_layout(
        yaxis_title="Latency (ms)",
        margin=dict(t=20, b=20),
        height=300,
    )
    st.plotly_chart(fig_latency, width="stretch")

    # -- Radar chart ----------------------------------------------------------
    st.subheader("Capability Radar")

    categories = [
        "Quality", "Speed", "Cost Efficiency",
        "Context Window", "Structured Output", "Tool Support",
    ]

    fig_radar = go.Figure()
    for m in selected_models:
        caps = m["capabilities"]
        pricing = m["pricing"]

        # Normalize metrics to 0-1 scale
        max_latency = 1500
        max_context = 250000
        max_price = 0.02

        quality = m.get("quality_score", 0.5)  # Default 0.5 for MVP
        speed = max(0, 1 - m["typical_latency_ms"] / max_latency)
        cost_eff = max(0, 1 - (pricing["input_per_1k"] + pricing["output_per_1k"]) / max_price)
        ctx = min(1.0, caps["max_context_tokens"] / max_context)
        struct = 1.0 if caps["supports_structured_output"] else 0.0
        tools = 1.0 if caps["supports_tools"] else 0.0

        values = [quality, speed, cost_eff, ctx, struct, tools]
        values.append(values[0])  # Close the polygon

        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill="toself",
            name=m["model_id"],
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        margin=dict(t=40, b=40),
        height=450,
    )
    st.plotly_chart(fig_radar, width="stretch")

    # -- Cost calculator ------------------------------------------------------
    st.subheader("Cost Calculator")
    st.caption("Estimate cost for a specific request")

    calc_model = st.selectbox("Model", selected_ids, key="calc_model")
    input_tokens = st.number_input("Input Tokens", min_value=1, value=500, step=50)
    output_tokens = st.number_input("Output Tokens", min_value=1, value=256, step=50)

    model_data = next(m for m in selected_models if m["model_id"] == calc_model)
    input_cost = input_tokens / 1000 * model_data["pricing"]["input_per_1k"]
    output_cost = output_tokens / 1000 * model_data["pricing"]["output_per_1k"]
    total_cost = input_cost + output_cost

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Input Cost", f"${input_cost:.6f}")
    with col2:
        st.metric("Output Cost", f"${output_cost:.6f}")
    with col3:
        st.metric("Total Cost", f"${total_cost:.6f}")
