from app.graph.state import RepoJudgeState
from app.tools.repository import validate_github_url


def validate_url(state: RepoJudgeState) -> dict[str, object]:
    return {
        "repository_url": validate_github_url(state["repository_url"]),
        "current_stage": "validate_url",
    }
