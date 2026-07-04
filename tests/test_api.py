from fastapi.testclient import TestClient

from agentos.api import app

client = TestClient(app)

_REQUEST = {
    "question_id": "q",
    "requirements": [
        {"id": "r1", "text": "Personal data is retained no longer than 24 months."},
        {"id": "r2", "text": "Data deletion requests are honored within 30 days."},
    ],
    "sources": [{"id": "s1", "kind": "plain_text", "uri": "samples/data_retention_policy.md"}],
    "principal": {"id": "o", "roles": ["owner"]},
}


def _verdicts(response):
    return {finding["requirement_id"]: finding["verdict"] for finding in response.json()["findings"]}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_requires_api_key():
    assert client.post("/compliance/check", json=_REQUEST).status_code == 401


def test_compliance_check_returns_findings():
    response = client.post("/compliance/check", headers={"X-API-Key": "dev-key"}, json=_REQUEST)
    assert response.status_code == 200
    verdicts = _verdicts(response)
    assert verdicts["r1"] == "satisfied"
    assert verdicts["r2"] == "satisfied"


def test_rbac_enforced_via_api():
    clerk_request = dict(_REQUEST, principal={"id": "c", "roles": ["clerk"]})
    response = client.post("/compliance/check", headers={"X-API-Key": "dev-key"}, json=clerk_request)
    assert response.status_code == 200
    assert _verdicts(response)["r1"] != "satisfied"


def test_rejects_unknown_role():
    bad_request = dict(_REQUEST, principal={"id": "x", "roles": ["wizard"]})
    response = client.post("/compliance/check", headers={"X-API-Key": "dev-key"}, json=bad_request)
    assert response.status_code == 400
