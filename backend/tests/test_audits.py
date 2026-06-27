import uuid

import pytest
from app.core.config import Settings
from app.db.models import AuditTask
from app.db.session import Base, SessionLocal, engine
from app.schemas.audit import AuditCreate, TaskStatus
from app.services.audits import AuditCapacityError, create_task, recover_interrupted_tasks
from sqlalchemy import delete


def test_audit_queue_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(
        "app.services.audits.get_settings",
        lambda: Settings(max_queued_audits=1),
    )
    first_id = ""
    with SessionLocal() as db:
        db.execute(
            delete(AuditTask).where(
                AuditTask.status.in_([TaskStatus.PENDING.value, TaskStatus.RUNNING.value])
            )
        )
        db.commit()
        first = create_task(
            db,
            AuditCreate(repository_url="https://github.com/example/one"),
        )
        first_id = first.id
        with pytest.raises(AuditCapacityError):
            create_task(
                db,
                AuditCreate(repository_url="https://github.com/example/two"),
            )
        db.execute(delete(AuditTask).where(AuditTask.id == first_id))
        db.commit()


def test_restart_recovery_marks_active_tasks_failed() -> None:
    Base.metadata.create_all(bind=engine)
    task_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(
            AuditTask(
                id=task_id,
                repository_url="https://github.com/example/interrupted",
                mode="professional",
                run_tests=False,
                status=TaskStatus.RUNNING.value,
                current_stage="security_scan",
            )
        )
        db.commit()
    assert recover_interrupted_tasks() >= 1
    with SessionLocal() as db:
        task = db.get(AuditTask, task_id)
        assert task is not None
        assert task.status == TaskStatus.FAILED.value
        assert task.current_stage == "interrupted"
        db.delete(task)
        db.commit()
