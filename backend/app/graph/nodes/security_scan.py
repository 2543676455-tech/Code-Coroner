from pathlib import Path

from app.core.config import get_settings
from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.scanners.security import scan_security


def security_scan(state: RepoJudgeState) -> dict[str, object]:
    try:
        findings = scan_security(
            Path(state["repository_path"]),
            get_settings().max_file_bytes,
        )
        return {"security_findings": findings, "current_stage": "security_scan"}
    except Exception as exc:
        return {
            "security_findings": [],
            "errors": record_error(state, "security_scan", exc),
            "current_stage": "security_scan",
        }
