from pathlib import Path

from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.schemas.audit import RepositoryMetadata
from app.tools.repository import collect_metadata


def collect_repository_metadata(state: RepoJudgeState) -> dict[str, object]:
    try:
        metadata = collect_metadata(Path(state["repository_path"]), state["repository_url"])
        return {"repository_metadata": metadata, "current_stage": "collect_repository_metadata"}
    except Exception as exc:
        return {
            "repository_metadata": RepositoryMetadata(url=state["repository_url"]),
            "errors": record_error(state, "collect_repository_metadata", exc),
            "current_stage": "collect_repository_metadata",
        }
