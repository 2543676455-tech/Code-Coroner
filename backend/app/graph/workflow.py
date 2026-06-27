from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.graph.nodes.analyze_project_structure import analyze_project_structure
from app.graph.nodes.analyze_readme import analyze_readme
from app.graph.nodes.calculate_scores import calculate_scores
from app.graph.nodes.clone_repository import clone_repository
from app.graph.nodes.collect_repository_metadata import collect_repository_metadata
from app.graph.nodes.extract_claims import extract_claims
from app.graph.nodes.generate_report import generate_report
from app.graph.nodes.inspect_engineering_quality import inspect_engineering_quality
from app.graph.nodes.sandbox_test import sandbox_test
from app.graph.nodes.security_scan import security_scan
from app.graph.nodes.validate_url import validate_url
from app.graph.nodes.verify_claims import verify_claims
from app.graph.state import RepoJudgeState


def _test_route(state: RepoJudgeState) -> str:
    return "sandbox_test" if state.get("run_tests", False) else "calculate_scores"


def build_workflow() -> Any:
    graph = StateGraph(RepoJudgeState)
    nodes = {
        "validate_url": validate_url,
        "clone_repository": clone_repository,
        "collect_repository_metadata": collect_repository_metadata,
        "analyze_readme": analyze_readme,
        "extract_claims": extract_claims,
        "analyze_project_structure": analyze_project_structure,
        "verify_claims": verify_claims,
        "inspect_engineering_quality": inspect_engineering_quality,
        "security_scan": security_scan,
        "sandbox_test": sandbox_test,
        "calculate_scores": calculate_scores,
        "generate_report": generate_report,
    }
    for name, node in nodes.items():
        retry_policy = (
            RetryPolicy(max_attempts=2, retry_on=(RuntimeError, TimeoutError))
            if name == "clone_repository"
            else None
        )
        graph.add_node(name, node, retry_policy=retry_policy)
    ordered = [
        "validate_url",
        "clone_repository",
        "collect_repository_metadata",
        "analyze_readme",
        "extract_claims",
        "analyze_project_structure",
        "verify_claims",
        "inspect_engineering_quality",
        "security_scan",
    ]
    graph.add_edge(START, ordered[0])
    for source, target in zip(ordered, ordered[1:], strict=False):
        graph.add_edge(source, target)
    graph.add_conditional_edges("security_scan", _test_route)
    graph.add_edge("sandbox_test", "calculate_scores")
    graph.add_edge("calculate_scores", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()
