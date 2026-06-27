from pathlib import Path

import pytest
from app.agents.llm import FakeLLM
from app.core.config import Settings
from app.graph.nodes.verify_claims import verify_claims
from app.scanners.claims import extract_claims

FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def test_llm_only_explains_bounded_rule_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        llm_base_url="https://llm.example/v1",
        llm_api_key="test-key",
        llm_model="fake",
    )
    monkeypatch.setattr("app.graph.nodes.verify_claims.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.graph.nodes.verify_claims.OpenAICompatibleClient",
        lambda _: FakeLLM("Only the supplied evidence was considered."),
    )
    state = {
        "repository_path": str(FIXTURE),
        "claims": extract_claims((FIXTURE / "README.md").read_text(encoding="utf-8")),
        "errors": [],
    }
    result = verify_claims(state)  # type: ignore[arg-type]
    claims = result["claims"]
    assert isinstance(claims, list)
    assert all("LLM evidence explanation" in claim.reason for claim in claims)
