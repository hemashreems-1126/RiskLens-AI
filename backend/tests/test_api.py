from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_full_investigation_flow():
    with TestClient(app) as client:
        r = client.get("/api/dashboard/summary")
        assert r.status_code == 200

        r = client.get("/api/alerts")
        assert r.status_code == 200
        alerts = r.json()
        assert len(alerts) > 0

        r = client.post("/api/investigations", json={"alert_id": alerts[0]["alert_id"]})
        assert r.status_code == 200
        inv = r.json()
        assert inv["decision"] in ("ALLOW", "REVIEW", "BLOCK")
        assert inv["risk_score"] is not None
        assert len(inv["agent_events"]) >= 8  # planner..audit_report

        inv_id = inv["investigation_id"]
        r = client.get(f"/api/investigations/{inv_id}/audit")
        assert r.status_code == 200
        assert len(r.json()) > 0

        r = client.post(f"/api/investigations/{inv_id}/review", json={"reviewer_decision": "ALLOW"})
        assert r.status_code == 200
        assert r.json()["decision"] == "ALLOW"

        r = client.post(f"/api/investigations/{inv_id}/feedback", json={"was_correct": True})
        assert r.status_code == 200


def test_investigation_missing_alert_returns_404():
    with TestClient(app) as client:
        r = client.post("/api/investigations", json={"alert_id": "does-not-exist"})
        assert r.status_code == 404


def test_review_rejects_invalid_decision():
    with TestClient(app) as client:
        r = client.get("/api/alerts")
        alert_id = r.json()[0]["alert_id"]
        r = client.post("/api/investigations", json={"alert_id": alert_id})
        inv_id = r.json()["investigation_id"]
        r = client.post(f"/api/investigations/{inv_id}/review", json={"reviewer_decision": "MAYBE"})
        assert r.status_code == 400
