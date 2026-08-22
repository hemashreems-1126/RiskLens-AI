"""Tests for the LangGraph state transitions, including the bounded
insufficient-evidence loop."""
from app.graph.investigation_graph import build_investigation_graph, _route_after_risk


def test_graph_builds_and_compiles():
    graph = build_investigation_graph()
    assert graph is not None


def test_route_after_risk_loops_when_insufficient():
    state = {"sufficient_evidence": False, "loop_number": 0}
    assert _route_after_risk(state) == "loop_back"


def test_route_after_risk_proceeds_when_sufficient():
    state = {"sufficient_evidence": True, "loop_number": 0}
    assert _route_after_risk(state) == "proceed"


def test_route_after_risk_stops_looping_at_max():
    state = {"sufficient_evidence": False, "loop_number": 2}  # MAX_INVESTIGATION_LOOPS default = 2
    assert _route_after_risk(state) == "proceed"
