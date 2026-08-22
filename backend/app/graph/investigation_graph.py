"""
The real LangGraph state graph for RiskLens AI. This is not a disguised
sequential script — routing after `risk_assessment` is a genuine
conditional edge, and the evidence/risk loop is a real cycle in the graph,
bounded by MAX_INVESTIGATION_LOOPS so it cannot run forever.

Graph shape:

  planner -> evidence -> behavior -> network -> compliance -> risk_assessment
        risk_assessment --(insufficient & loops remain)--> evidence_loop -> risk_assessment
        risk_assessment --(sufficient OR loops exhausted)--> decision -> explainability -> audit_report -> END
"""
from __future__ import annotations
from langgraph.graph import StateGraph, END

from app.graph.state import CaseState
from app.agents import nodes
from app.config.settings import get_settings

settings = get_settings()


def _route_after_risk(state: CaseState) -> str:
    sufficient = state.get("sufficient_evidence", True)
    loop_number = state.get("loop_number", 0)
    if not sufficient and loop_number < settings.MAX_INVESTIGATION_LOOPS:
        return "loop_back"
    return "proceed"


def build_investigation_graph():
    graph = StateGraph(CaseState)

    graph.add_node("planner", nodes.planner_node)
    graph.add_node("evidence_agent", nodes.evidence_agent_node)
    graph.add_node("behavior_agent", nodes.behavior_agent_node)
    graph.add_node("network_agent", nodes.network_agent_node)
    graph.add_node("compliance_agent", nodes.compliance_agent_node)
    graph.add_node("risk_assessment", nodes.risk_assessment_node)
    graph.add_node("evidence_loop", nodes.evidence_loop_node)
    graph.add_node("decision_stage", nodes.decision_node)
    graph.add_node("explainability", nodes.explainability_node)
    graph.add_node("audit_report", nodes.audit_report_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "evidence_agent")
    graph.add_edge("evidence_agent", "behavior_agent")
    graph.add_edge("behavior_agent", "network_agent")
    graph.add_edge("network_agent", "compliance_agent")
    graph.add_edge("compliance_agent", "risk_assessment")

    graph.add_conditional_edges(
        "risk_assessment",
        _route_after_risk,
        {"loop_back": "evidence_loop", "proceed": "decision_stage"},
    )
    graph.add_edge("evidence_loop", "risk_assessment")

    graph.add_edge("decision_stage", "explainability")
    graph.add_edge("explainability", "audit_report")
    graph.add_edge("audit_report", END)

    return graph.compile()


_compiled_graph = None


def get_investigation_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_investigation_graph()
    return _compiled_graph
