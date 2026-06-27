from pathlib import Path

from app.core.config import get_settings
from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.schemas.audit import TestResult
from app.services.sandbox import run_tests_in_sandbox


def sandbox_test(state: RepoJudgeState) -> dict[str, object]:
    try:
        result = run_tests_in_sandbox(Path(state["repository_path"]), get_settings())
        return {"test_result": result, "current_stage": "sandbox_test"}
    except Exception as exc:
        return {
            "test_result": TestResult(status="skipped", reason="Sandbox execution failed safely."),
            "errors": record_error(state, "sandbox_test", exc),
            "current_stage": "sandbox_test",
        }
