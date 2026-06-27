from pathlib import Path

from app.core.config import get_settings
from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.scanners.structure import analyze_structure
from app.schemas.audit import ProjectStructure


def analyze_project_structure(state: RepoJudgeState) -> dict[str, object]:
    try:
        structure = analyze_structure(
            Path(state["repository_path"]),
            get_settings().max_file_bytes,
        )
        return {
            "project_structure": structure,
            "current_stage": "analyze_project_structure",
        }
    except Exception as exc:
        return {
            "project_structure": ProjectStructure(),
            "errors": record_error(state, "analyze_project_structure", exc),
            "current_stage": "analyze_project_structure",
        }
