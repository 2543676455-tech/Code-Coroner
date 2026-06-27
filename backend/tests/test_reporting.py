from datetime import UTC, datetime

from app.schemas.audit import (
    AuditMode,
    AuditReportData,
    EngineeringCheck,
    RepositoryMetadata,
    ScoreDetail,
    Scores,
)
from app.schemas.audit import (
    TestResult as AuditTestResult,
)
from app.services.reporting import build_roast, report_to_markdown


def test_report_markdown_and_roast() -> None:
    report = AuditReportData(
        task_id="test",
        repository_url="https://github.com/a/b",
        mode=AuditMode.ROAST,
        generated_at=datetime.now(UTC),
        llm_enabled=False,
        repository_metadata=RepositoryMetadata(name="b", owner="a", url="https://github.com/a/b"),
        claims=[],
        engineering_checks=[],
        security_findings=[],
        test_result=AuditTestResult(status="skipped"),
        scores=Scores(
            readme_credibility=ScoreDetail(score=50),
            production_readiness=ScoreDetail(score=50),
            learning_value=ScoreDetail(score=50),
            wrapper_index=ScoreDetail(score=50),
        ),
        summary="Evidence-first summary.",
    )
    report.roast = build_roast(report)
    markdown = report_to_markdown(report)
    assert "README credibility" in markdown
    assert "Project Structure" in markdown
    assert report.roast


def test_roast_recommends_only_failed_checks() -> None:
    report = AuditReportData(
        task_id="test",
        repository_url="https://github.com/a/b",
        mode=AuditMode.ROAST,
        generated_at=datetime.now(UTC),
        llm_enabled=False,
        repository_metadata=RepositoryMetadata(name="b", owner="a", url="https://github.com/a/b"),
        claims=[],
        engineering_checks=[
            EngineeringCheck(id="tests", name="Test suite", status="pass", message="present"),
            EngineeringCheck(id="ci", name="CI workflow", status="pass", message="present"),
            EngineeringCheck(id="dockerfile", name="Dockerfile", status="fail", message="missing"),
        ],
        security_findings=[],
        test_result=AuditTestResult(status="skipped"),
        scores=Scores(
            readme_credibility=ScoreDetail(score=40),
            production_readiness=ScoreDetail(score=30),
            learning_value=ScoreDetail(score=50),
            wrapper_index=ScoreDetail(score=50),
        ),
        summary="summary",
    )
    roast = build_roast(report)
    assert roast and "Dockerfile" in roast
    assert "测试" not in roast
