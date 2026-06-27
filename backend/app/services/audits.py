import json
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuditReport, AuditTask
from app.db.session import SessionLocal
from app.graph.workflow import build_workflow
from app.schemas.audit import AuditCreate, AuditMode, AuditReportData, TaskStatus

logger = structlog.get_logger()
_semaphore = threading.BoundedSemaphore(get_settings().max_concurrent_audits)


class AuditCapacityError(RuntimeError):
    """Raised when the bounded in-process audit queue is full."""


def create_task(db: Session, request: AuditCreate) -> AuditTask:
    active = db.scalar(
        select(func.count())
        .select_from(AuditTask)
        .where(AuditTask.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value]))
    )
    if int(active or 0) >= get_settings().max_queued_audits:
        raise AuditCapacityError("Audit queue is full; retry after an existing task finishes")
    task = AuditTask(
        id=str(uuid.uuid4()),
        repository_url=request.repository_url,
        mode=request.mode.value,
        run_tests=request.run_tests,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> AuditTask | None:
    return db.get(AuditTask, task_id)


def get_report(db: Session, task_id: str) -> AuditReport | None:
    return db.scalar(select(AuditReport).where(AuditReport.task_id == task_id))


def recover_interrupted_tasks() -> int:
    with SessionLocal() as db:
        result = db.execute(
            update(AuditTask)
            .where(AuditTask.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value]))
            .values(
                status=TaskStatus.FAILED.value,
                current_stage="interrupted",
                error_message="Audit was interrupted by an application restart.",
            )
        )
        db.commit()
        return int(getattr(result, "rowcount", 0) or 0)


def execute_audit(task_id: str, github_token: str | None = None) -> None:
    with _semaphore, SessionLocal() as db:
        task = db.get(AuditTask, task_id)
        if task is None:
            return
        task.status = TaskStatus.RUNNING.value
        task.current_stage = "starting"
        db.commit()
        state: dict[str, Any] = {
            "task_id": task.id,
            "repository_url": task.repository_url,
            "mode": AuditMode(task.mode),
            "run_tests": task.run_tests,
            "github_token": github_token,
            "llm_enabled": get_settings().llm_enabled,
            "errors": [],
        }
        repository_path: str | None = None
        deadline = time.monotonic() + get_settings().analysis_timeout_seconds
        try:
            workflow = build_workflow()
            for update in workflow.stream(state, stream_mode="updates"):
                if time.monotonic() > deadline:
                    raise TimeoutError("Repository analysis exceeded the configured time limit")
                for node_name, values in update.items():
                    if isinstance(values, dict):
                        state.update(values)
                        repository_path = state.get("repository_path", repository_path)
                    task.current_stage = node_name
                    db.commit()
            validated = AuditReportData.model_validate(state["report"])
            report = AuditReport(
                id=str(uuid.uuid4()),
                task_id=task.id,
                repository_metadata_json=json.dumps(
                    validated.repository_metadata.model_dump(mode="json"), ensure_ascii=False
                ),
                claims_json=json.dumps(
                    [item.model_dump(mode="json") for item in validated.claims], ensure_ascii=False
                ),
                findings_json=json.dumps(
                    {
                        "engineering_checks": [
                            item.model_dump(mode="json") for item in validated.engineering_checks
                        ],
                        "security_findings": [
                            item.model_dump(mode="json") for item in validated.security_findings
                        ],
                        "test_result": validated.test_result.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
                scores_json=json.dumps(validated.scores.model_dump(mode="json"), ensure_ascii=False),
                report_json=validated.model_dump_json(),
                report_markdown=state["report_markdown"],
            )
            db.add(report)
            task.status = TaskStatus.COMPLETED.value
            task.current_stage = "completed"
            db.commit()
            logger.info("audit_completed", task_id=task_id)
        except Exception as exc:
            task.status = TaskStatus.FAILED.value
            task.current_stage = state.get("current_stage", task.current_stage)
            task.error_message = str(exc)[:1000]
            db.commit()
            logger.exception("audit_failed", task_id=task_id, stage=task.current_stage)
        finally:
            if repository_path:
                shutil.rmtree(Path(repository_path).parent, ignore_errors=True)
