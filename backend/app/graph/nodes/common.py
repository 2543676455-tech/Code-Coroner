from typing import Any

from app.graph.state import RepoJudgeState


def record_error(state: RepoJudgeState, stage: str, exc: Exception) -> list[dict[str, Any]]:
    return [
        *state.get("errors", []),
        {"stage": stage, "error": type(exc).__name__, "message": str(exc)[:500]},
    ]
