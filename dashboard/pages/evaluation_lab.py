# ---------------------------------------------------------------------------
# 5_evaluation_lab.py — Evaluation Lab dashboard page
# ---------------------------------------------------------------------------
# Evaluation framework and results.  Uses mock data until Phase 7
# (evaluation dataset + framework) is implemented.
# ---------------------------------------------------------------------------

import os
import sys

_root = os.getcwd()
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import plotly.graph_objects as go

from dashboard.mock_data import MOCK_EVALUATION_EXAMPLES, MOCK_EVALUATION_RESULTS


def render() -> None:
    st.title("Evaluation Lab")
    st.info("Showing demo data. Full evaluation framework requires Phase 7.")

    # -- Dataset summary ------------------------------------------------------
    st.subheader("Datasets")

    for ds in MOCK_EVALUATION_RESULTS:
        with st.expander(f"**{ds['dataset']}** ({ds['examples']} examples)", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Router Accuracy", f"{ds['router_accuracy']*100:.1f}%")
            with col2:
                st.metric("Strongest Accuracy", f"{ds['strongest_accuracy']*100:.1f}%")
            with col3:
                st.metric("Cheapest Accuracy", f"{ds['cheapest_accuracy']*100:.1f}%")

            st.metric(
                "Cost Savings vs Strongest",
                f"{ds['savings_vs_strongest']*100:.0f}%",
            )

    st.markdown("---")

    # -- Baseline comparison --------------------------------------------------
    st.subheader("Baseline Comparison")

    if MOCK_EVALUATION_RESULTS:
        ds = MOCK_EVALUATION_RESULTS[0]  # Use first dataset

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Router",
            x=["Accuracy", "Avg Cost (x1000)", "Avg Latency (ms)"],
            y=[
                ds["router_accuracy"] * 100,
                ds["router_avg_cost"] * 1000,
                ds["router_avg_latency_ms"],
            ],
            marker_color="#3b82f6",
        ))
        fig.add_trace(go.Bar(
            name="Strongest",
            x=["Accuracy", "Avg Cost (x1000)", "Avg Latency (ms)"],
            y=[
                ds["strongest_accuracy"] * 100,
                ds["strongest_avg_cost"] * 1000,
                ds["strongest_avg_latency_ms"],
            ],
            marker_color="#22c55e",
        ))
        fig.add_trace(go.Bar(
            name="Cheapest",
            x=["Accuracy", "Avg Cost (x1000)", "Avg Latency (ms)"],
            y=[
                ds["cheapest_accuracy"] * 100,
                ds["cheapest_avg_cost"] * 1000,
                ds["cheapest_avg_latency_ms"],
            ],
            marker_color="#f59e0b",
        ))
        fig.update_layout(
            barmode="group",
            margin=dict(t=20, b=20),
            height=400,
        )
        st.plotly_chart(fig, width="stretch")

    # -- Spec targets ---------------------------------------------------------
    st.subheader("Engineering Targets")

    targets = [
        ("Router quality >= 90% of strongest", "92%", "97%", True),
        ("Cost reduction >= 30%", "34%", "—", True),
        ("Held-out dataset >= 20 examples", "20", "20", True),
        ("Unauthorized tool calls = 0", "0", "—", True),
    ]

    target_data = [
        {
            "Target": t[0],
            "Achieved": t[1],
            "Baseline": t[2],
            "Met": "Yes" if t[3] else "No",
        }
        for t in targets
    ]
    st.dataframe(target_data, width="stretch")

    st.markdown("---")

    # -- Example results table ------------------------------------------------
    st.subheader("Example Results")

    examples_data = [
        {
            "ID": e["id"],
            "Input": e["input"][:50] + "..." if len(e["input"]) > 50 else e["input"],
            "Expected": e["expected"],
            "Router Output": e["router_output"],
            "Model": e["router_model"],
            "Correct": "Yes" if e["correct"] else "No",
        }
        for e in MOCK_EVALUATION_EXAMPLES
    ]
    st.dataframe(examples_data, width="stretch")

    # -- Run evaluation button (placeholder) ----------------------------------
    st.markdown("---")
    st.subheader("Run Evaluation")

    col1, col2 = st.columns(2)
    with col1:
        eval_dataset = st.selectbox(
            "Dataset",
            [ds["dataset"] for ds in MOCK_EVALUATION_RESULTS],
        )
    with col2:
        eval_model = st.selectbox(
            "Model Strategy",
            ["router", "strongest", "cheapest"],
        )

    if st.button("Run Evaluation", type="primary"):
        st.warning("Full evaluation framework coming in Phase 7.")
        st.info("This will run the selected model strategy against the chosen dataset and report accuracy, cost, and latency metrics.")
