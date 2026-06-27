from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.schemas.audit import ProjectStructure, RepositoryMetadata, TestResult
from app.scoring.engine import calculate_scores as calculate


def calculate_scores(state: RepoJudgeState) -> dict[str, object]:
    try:
        test_result = state.get(
            "test_result",
            TestResult(status="skipped", reason="Sandbox tests were not requested."),
        )
        scores = calculate(
            state.get("repository_metadata", RepositoryMetadata(url=state["repository_url"])),
            state.get("project_structure", ProjectStructure()),
            state.get("claims", []),
            state.get("engineering_checks", []),
            state.get("security_findings", []),
            test_result,
        )
        return {
            "test_result": test_result,
            "scores": scores,
            "current_stage": "calculate_scores",
        }
    except Exception as exc:
        return {
            "errors": record_error(state, "calculate_scores", exc),
            "current_stage": "calculate_scores",
        }
