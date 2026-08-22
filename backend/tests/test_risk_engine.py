from app.risk.risk_engine import compute_risk_score, risk_level_from_score, decision_from_risk, WEIGHTS


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6


def test_compute_risk_score_all_zero():
    score, breakdown = compute_risk_score({})
    assert score == 0.0


def test_compute_risk_score_all_max():
    signals = {k: 1.0 for k in WEIGHTS}
    score, breakdown = compute_risk_score(signals)
    assert score == 100.0


def test_risk_level_bands():
    assert risk_level_from_score(10) == "LOW"
    assert risk_level_from_score(40) == "MEDIUM"
    assert risk_level_from_score(65) == "HIGH"
    assert risk_level_from_score(90) == "CRITICAL"


def test_decision_critical_blocks():
    decision, rationale = decision_from_risk("CRITICAL", True)
    assert decision == "BLOCK"


def test_decision_insufficient_evidence_forces_review():
    decision, rationale = decision_from_risk("CRITICAL", False)
    assert decision == "REVIEW"


def test_decision_human_override_wins():
    decision, rationale = decision_from_risk("CRITICAL", True, human_override="ALLOW")
    assert decision == "ALLOW"


def test_decision_escalate_maps_to_review():
    decision, rationale = decision_from_risk("LOW", True, human_override="ESCALATE")
    assert decision == "REVIEW"
