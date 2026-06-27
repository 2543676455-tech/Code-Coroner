from pathlib import Path

from app.core.config import get_settings
from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.scanners.engineering import inspect_engineering


def inspect_engineering_quality(state: RepoJudgeState) -> dict[str, object]:
    try:
        checks = inspect_engineering(
            Path(state["repository_path"]),
            get_settings().max_file_bytes,
        )
        return {"engineering_checks": checks, "current_stage": "inspect_engineering_quality"}
    except Exception as exc:
        return {
            "engineering_checks": [],
            "errors": record_error(state, "inspect_engineering_quality", exc),
            "current_stage": "inspect_engineering_quality",
        }
