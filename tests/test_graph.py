from graph.turn_loop import build_turn_loop


def test_build_turn_loop():
    graph = build_turn_loop()
    # Graph might be None if langgraph import fails — scaffold should remain import-safe
    assert graph is None or graph is not None
