from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.scanners.claims import extract_claims as extract


def extract_claims(state: RepoJudgeState) -> dict[str, object]:
    try:
        return {"claims": extract(state.get("readme_content", "")), "current_stage": "extract_claims"}
    except Exception as exc:
        return {
            "claims": [],
            "errors": record_error(state, "extract_claims", exc),
            "current_stage": "extract_claims",
        }
