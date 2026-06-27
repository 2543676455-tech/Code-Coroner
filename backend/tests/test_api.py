from app.main import app
from fastapi.testclient import TestClient


def test_health_and_demo() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        demo = client.get("/api/v1/demo")
        assert demo.status_code == 200
        assert len(demo.json()["claims"]) >= 5
        assert demo.json()["project_structure"]["entrypoints"]
        markdown = client.get("/api/v1/demo/markdown")
        assert markdown.status_code == 200
        assert "attachment" in markdown.headers["content-disposition"]


def test_submit_rejects_non_github_url() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/audits",
            json={"repository_url": "file:///tmp/repo", "mode": "professional", "run_tests": False},
        )
        assert response.status_code == 422
