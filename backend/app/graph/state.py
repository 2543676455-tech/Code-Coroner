from typing import Any, TypedDict

from app.schemas.audit import (
    AuditMode,
    Claim,
    EngineeringCheck,
    Evidence,
    ProjectStructure,
    RepositoryMetadata,
    Scores,
    SecurityFinding,
    TestResult,
)


class RepoJudgeState(TypedDict, total=False):
    task_id: str
    repository_url: str
    repository_path: str
    repository_metadata: RepositoryMetadata
    project_structure: ProjectStructure
    readme_content: str
    claims: list[Claim]
    evidence: list[Evidence]
    engineering_checks: list[EngineeringCheck]
    security_findings: list[SecurityFinding]
    test_result: TestResult
    scores: Scores
    report: dict[str, Any]
    report_markdown: str
    errors: list[dict[str, Any]]
    current_stage: str
    mode: AuditMode
    run_tests: bool
    github_token: str | None
    llm_enabled: bool
