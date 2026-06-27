from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.services.reporting import make_report, report_to_markdown


def generate_report(state: RepoJudgeState) -> dict[str, object]:
    try:
        report = make_report(dict(state))
        return {
            "report": report.model_dump(mode="json"),
            "report_markdown": report_to_markdown(report),
            "current_stage": "generate_report",
        }
    except Exception as exc:
        return {
            "errors": record_error(state, "generate_report", exc),
            "current_stage": "generate_report",
        }
