import shutil
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.graph.state import RepoJudgeState
from app.tools.repository import clone_repository as clone


def clone_repository(state: RepoJudgeState) -> dict[str, object]:
    parent = Path(tempfile.mkdtemp(prefix=f"repojudge-{state['task_id'][:8]}-"))
    try:
        path = clone(
            state["repository_url"],
            parent / "repository",
            get_settings(),
            state.get("github_token"),
        )
    except Exception:
        shutil.rmtree(parent, ignore_errors=True)
        raise
    return {"repository_path": str(path), "current_stage": "clone_repository"}
