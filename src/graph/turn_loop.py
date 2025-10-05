from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger

try:
    # LangGraph API evolves; keep import minimal to avoid runtime issues if version changes.
    from langgraph.graph import StateGraph
except Exception as e:  # pragma: no cover - defensive
    StateGraph = None  # type: ignore
    logger.warning(f"LangGraph not available: {e}")


def build_turn_loop() -> Optional[Any]:
    """
    Return a minimal LangGraph StateGraph, or None if LangGraph is unavailable.
    """
    if StateGraph is None:
        return None

    def identity_node(state: Dict[str, Any]) -> Dict[str, Any]:
        state["turns"] = state.get("turns", 0) + 1
        return state

    graph = StateGraph(dict)
    graph.add_node("turn", identity_node)
    graph.set_entry_point("turn")
    return graph.compile()
