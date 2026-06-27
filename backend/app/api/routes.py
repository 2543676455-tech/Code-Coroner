import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.audit import AuditCreate, AuditCreated, AuditReportData, AuditTaskView
from app.services.audits import (
    AuditCapacityError,
    create_task,
    execute_audit,
    get_report,
    get_task,
)
from app.tools.repository import validate_github_url

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.post("/api/v1/audits", response_model=AuditCreated, status_code=status.HTTP_202_ACCEPTED)
def submit_audit(
    request: AuditCreate,
    background_tasks: BackgroundTasks,
    db: Database,
) -> AuditCreated:
    try:
        request.repository_url = validate_github_url(request.repository_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        task = create_task(db, request)
    except AuditCapacityError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    background_tasks.add_task(execute_audit, task.id, request.github_token)
    return AuditCreated(task_id=task.id)


@router.get("/api/v1/audits/{task_id}", response_model=AuditTaskView)
def audit_status(task_id: str, db: Database) -> AuditTaskView:
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Audit task not found")
    return AuditTaskView.model_validate(task)


@router.get("/api/v1/audits/{task_id}/report", response_model=AuditReportData)
def audit_report(task_id: str, db: Database) -> AuditReportData:
    report = get_report(db, task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Audit report is not ready")
    return AuditReportData.model_validate_json(report.report_json)


@router.get("/api/v1/audits/{task_id}/report/markdown")
def audit_report_markdown(task_id: str, db: Database) -> Response:
    report = get_report(db, task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Audit report is not ready")
    return Response(
        report.report_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="repojudge-{task_id}.md"'},
    )


@router.get("/api/v1/demo", response_model=AuditReportData)
def demo_report() -> AuditReportData:
    path = Path(__file__).resolve().parents[3] / "examples" / "sample_report.json"
    return AuditReportData.model_validate(json.loads(path.read_text(encoding="utf-8")))


@router.get("/api/v1/demo/markdown")
def demo_report_markdown() -> Response:
    path = Path(__file__).resolve().parents[3] / "examples" / "sample_report.md"
    return Response(
        path.read_text(encoding="utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="repojudge-demo.md"'},
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "repojudge"}
