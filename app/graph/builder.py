# ---------------------------------------------------------------------------
# builder.py — LangGraph StateGraph construction
# ---------------------------------------------------------------------------
# Builds and compiles the state machine with persistent checkpointing.
# ---------------------------------------------------------------------------

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    analyze_node,
    evaluate_node,
    execute_node,
    filter_node,
    finalize_node,
    route_node,
)
from app.graph.router import decide_next
from app.graph.state import GraphState


def build_graph() -> StateGraph:
    """Construct and compile the LangGraph workflow.

    The compiled graph is ready to be invoked with ``graph.invoke()`` or
    ``graph.ainvoke()``.

    Returns
    -------
    CompiledGraph
        A compiled StateGraph with MemorySaver checkpointing.
    """
    graph = StateGraph(GraphState)

    # -- Nodes ----------------------------------------------------------------
    graph.add_node("analyze", analyze_node)
    graph.add_node("filter", filter_node)
    graph.add_node("route", route_node)
    graph.add_node("execute", execute_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("finalize", finalize_node)

    # -- Edges ----------------------------------------------------------------
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "filter")
    graph.add_edge("filter", "route")

    # filter → route may fail (no eligible models) — short-circuit to finalize
    def after_filter(state: GraphState) -> str:
        if state.get("error") or not state.get("selected_model"):
            return "finalize"
        return "execute"

    graph.add_conditional_edges("filter", after_filter, {"execute": "execute", "finalize": "finalize"})

    graph.add_edge("execute", "evaluate")

    # evaluate → accept/revise/escalate
    graph.add_conditional_edges("evaluate", decide_next, {"finalize": "finalize", "route": "route"})

    graph.add_edge("finalize", END)

    # -- Compile with checkpointing -------------------------------------------
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
