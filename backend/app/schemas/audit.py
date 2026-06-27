from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AuditMode(StrEnum):
    PROFESSIONAL = "professional"
    ROAST = "roast"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Evidence(BaseModel):
    type: Literal["file", "code", "config", "test", "log"]
    path: str
    line_start: int | None = None
    line_end: int | None = None
    excerpt: str = Field(max_length=1000)
    description: str


class Claim(BaseModel):
    id: str
    claim: str
    category: str
    verification_rules: list[str]
    status: Literal["verified", "partial", "unsupported", "unknown"] = "unknown"
    confidence: float = Field(default=0.0, ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)
    reason: str = ""


class EngineeringCheck(BaseModel):
    id: str
    name: str
    status: Literal["pass", "fail", "warn", "unknown"]
    weight: float = 1.0
    evidence: list[Evidence] = Field(default_factory=list)
    message: str


class SecurityFinding(BaseModel):
    rule_id: str
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    path: str
    line: int
    excerpt: str
    recommendation: str


class TestResult(BaseModel):
    status: Literal["passed", "failed", "skipped", "timeout"]
    exit_code: int | None = None
    duration_seconds: float = 0
    log: str = ""
    reason: str = ""


class ScoreDetail(BaseModel):
    score: int = Field(ge=0, le=100)
    additions: list[str] = Field(default_factory=list)
    deductions: list[str] = Field(default_factory=list)


class Scores(BaseModel):
    readme_credibility: ScoreDetail
    production_readiness: ScoreDetail
    learning_value: ScoreDetail
    wrapper_index: ScoreDetail


class RepositoryMetadata(BaseModel):
    name: str = ""
    owner: str = ""
    url: str
    default_branch: str = ""
    commit_sha: str = ""
    file_count: int = 0
    total_bytes: int = 0
    python_files: int = 0
    lines_of_python: int = 0


class ModuleMetric(BaseModel):
    path: str
    lines: int = Field(ge=0)


class ProjectStructure(BaseModel):
    top_level_entries: list[str] = Field(default_factory=list)
    package_directories: list[str] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)
    dependency_files: list[str] = Field(default_factory=list)
    configuration_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    largest_modules: list[ModuleMetric] = Field(default_factory=list)
    max_module_lines: int = Field(default=0, ge=0)
    architecture_notes: list[str] = Field(default_factory=list)


class AuditReportData(BaseModel):
    task_id: str
    repository_url: str
    mode: AuditMode
    generated_at: datetime
    llm_enabled: bool
    repository_metadata: RepositoryMetadata
    project_structure: ProjectStructure = Field(default_factory=ProjectStructure)
    claims: list[Claim]
    engineering_checks: list[EngineeringCheck]
    security_findings: list[SecurityFinding]
    test_result: TestResult
    scores: Scores
    summary: str
    roast: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)


class AuditCreate(BaseModel):
    repository_url: str
    mode: AuditMode = AuditMode.PROFESSIONAL
    run_tests: bool = False
    github_token: str | None = Field(default=None, exclude=True, min_length=1, max_length=256)


class AuditCreated(BaseModel):
    task_id: str


class AuditTaskView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    repository_url: str
    mode: AuditMode
    run_tests: bool
    status: TaskStatus
    current_stage: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
