from pathlib import Path

from app.graph.nodes.analyze_readme import analyze_readme
from app.graph.nodes.extract_claims import extract_claims
from app.graph.nodes.inspect_engineering_quality import inspect_engineering_quality
from app.graph.nodes.security_scan import security_scan
from app.graph.workflow import build_workflow

FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def test_langgraph_nodes_operate_on_local_fixture() -> None:
    state = {
        "task_id": "test",
        "repository_url": "https://github.com/example/sample",
        "repository_path": str(FIXTURE),
        "errors": [],
    }
    state.update(analyze_readme(state))  # type: ignore[arg-type]
    state.update(extract_claims(state))  # type: ignore[arg-type]
    state.update(inspect_engineering_quality(state))  # type: ignore[arg-type]
    state.update(security_scan(state))  # type: ignore[arg-type]
    assert state["claims"]
    assert state["engineering_checks"]
    assert state["current_stage"] == "security_scan"


def test_workflow_compiles() -> None:
    assert build_workflow() is not None
