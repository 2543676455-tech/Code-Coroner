from pathlib import Path
from subprocess import CompletedProcess

import pytest
from app.core.config import Settings
from app.tools.repository import clone_repository


def test_github_token_is_passed_by_environment_not_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        Path(command[-1]).mkdir(parents=True)
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("app.tools.repository.subprocess.run", fake_run)
    destination = tmp_path / "repo"
    clone_repository(
        "https://github.com/example/repo",
        destination,
        Settings(),
        token="github-secret-token",
    )
    assert "github-secret-token" not in " ".join(captured["command"])  # type: ignore[arg-type]
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["GIT_CONFIG_VALUE_0"] == "Authorization: Bearer github-secret-token"


def test_repository_file_count_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        del kwargs
        destination = Path(command[-1])
        destination.mkdir(parents=True)
        for index in range(101):
            (destination / f"{index}.py").write_text("", encoding="utf-8")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("app.tools.repository.subprocess.run", fake_run)
    with pytest.raises(RuntimeError, match="file limit"):
        clone_repository(
            "https://github.com/example/repo",
            tmp_path / "repo",
            Settings(max_repository_files=100),
        )
