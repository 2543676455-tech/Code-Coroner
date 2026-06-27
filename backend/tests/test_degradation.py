from pathlib import Path

import pytest
from app.agents.llm import OpenAICompatibleClient
from app.core.config import Settings
from app.services.sandbox import run_tests_in_sandbox


def test_docker_unavailable_is_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.services.sandbox.shutil.which", lambda _: None)
    result = run_tests_in_sandbox(tmp_path, Settings())
    assert result.status == "skipped"
    assert "unavailable" in result.reason


def test_llm_unconfigured_is_explicit() -> None:
    settings = Settings(llm_base_url="", llm_api_key="", llm_model="")
    assert not settings.llm_enabled
    with pytest.raises(ValueError, match="not configured"):
        OpenAICompatibleClient(settings)


def test_missing_pytest_configuration_skips_before_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "test_example.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    monkeypatch.setattr("app.services.sandbox._docker_available", lambda: True)
    result = run_tests_in_sandbox(tmp_path, Settings())
    assert result.status == "skipped"
    assert "configuration" in result.reason
