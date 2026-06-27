from app.core.scoring_rules import PRODUCTION_WEIGHTS
from app.schemas.audit import Claim, ProjectStructure, RepositoryMetadata
from app.schemas.audit import TestResult as AuditTestResult
from app.scoring.engine import calculate_scores


def make_claim(status: str) -> Claim:
    return Claim(
        id="claim_001",
        claim="Supports tests",
        category="testing",
        verification_rules=["tests exist"],
        status=status,  # type: ignore[arg-type]
    )


def test_scores_are_bounded_and_deterministic() -> None:
    metadata = RepositoryMetadata(
        name="sample",
        owner="owner",
        url="https://github.com/owner/sample",
        python_files=2,
        lines_of_python=100,
    )
    args = (
        metadata,
        ProjectStructure(),
        [make_claim("unsupported")],
        [],
        [],
        AuditTestResult(status="skipped"),
    )
    first = calculate_scores(*args)
    second = calculate_scores(*args)
    assert first == second
    for detail in first.model_dump().values():
        assert 0 <= detail["score"] <= 100


def test_production_weights_are_a_complete_percentage() -> None:
    assert sum(PRODUCTION_WEIGHTS.values()) == 100
