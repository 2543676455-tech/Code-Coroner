from pathlib import Path

from app.core.config import get_settings
from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.tools.repository import find_readme, safe_read


def analyze_readme(state: RepoJudgeState) -> dict[str, object]:
    try:
        root = Path(state["repository_path"])
        path = find_readme(root)
        content = safe_read(path, root, get_settings().max_file_bytes) if path else ""
        return {"readme_content": content, "current_stage": "analyze_readme"}
    except Exception as exc:
        return {
            "readme_content": "",
            "errors": record_error(state, "analyze_readme", exc),
            "current_stage": "analyze_readme",
        }
