from datetime import UTC, datetime
from typing import Any

from app.schemas.audit import AuditMode, AuditReportData


def build_summary(report: AuditReportData) -> str:
    scores = report.scores
    supported = sum(item.status == "verified" for item in report.claims)
    claim_summary = (
        f"{supported}/{len(report.claims)} detected README claims were verified."
        if report.claims
        else "No verifiable README claims were detected."
    )
    return (
        f"Audited {report.repository_metadata.name} using evidence-first rules. "
        f"{claim_summary} Production readiness is {scores.production_readiness.score}/100 with "
        f"{len(report.security_findings)} security finding(s)."
    )


def build_roast(report: AuditReportData) -> str | None:
    if report.mode != AuditMode.ROAST:
        return None
    unsupported = [claim for claim in report.claims if claim.status == "unsupported"]
    if unsupported:
        return (
            f"README 把“{unsupported[0].claim}”端上了桌，代码证据却还在路上。"
            "建议先补齐可运行实现和测试，再让文档负责宣传。"
        )
    if report.scores.production_readiness.score < 60:
        failed = [check.name for check in report.engineering_checks if check.status == "fail"]
        priorities = "、".join(failed[:3]) or "失败项"
        return (
            "项目已经会走路，但生产环境需要的是安全带、体检报告和应急预案。"
            f"当前证据明确缺少：{priorities}；建议按这些失败项逐一补齐。"
        )
    return "这次 README 基本没有吹过头。继续保持：让测试日志说话，比形容词更有说服力。"


def make_report(state: dict[str, Any]) -> AuditReportData:
    report = AuditReportData(
        task_id=state["task_id"],
        repository_url=state["repository_url"],
        mode=state["mode"],
        generated_at=datetime.now(UTC),
        llm_enabled=state.get("llm_enabled", False),
        repository_metadata=state["repository_metadata"],
        project_structure=state.get("project_structure", {}),
        claims=state.get("claims", []),
        engineering_checks=state.get("engineering_checks", []),
        security_findings=state.get("security_findings", []),
        test_result=state["test_result"],
        scores=state["scores"],
        summary="",
        errors=state.get("errors", []),
    )
    report.summary = build_summary(report)
    report.roast = build_roast(report)
    return report


def report_to_markdown(report: AuditReportData) -> str:
    lines = [
        f"# RepoJudge Audit: {report.repository_metadata.owner}/{report.repository_metadata.name}",
        "",
        f"- Repository: {report.repository_url}",
        f"- Generated: {report.generated_at.isoformat()}",
        f"- Mode: {report.mode.value}",
        f"- LLM semantic verification: {'enabled' if report.llm_enabled else 'not enabled'}",
        "",
        "## Scores",
        "",
        f"- README credibility: **{report.scores.readme_credibility.score}/100**",
        f"- Production readiness: **{report.scores.production_readiness.score}/100**",
        f"- Learning value: **{report.scores.learning_value.score}/100**",
        f"- Wrapper index: **{report.scores.wrapper_index.score}/100**",
        "",
        "## README Claims",
        "",
    ]
    for claim in report.claims:
        paths = ", ".join(f"`{item.path}:{item.line_start or 1}`" for item in claim.evidence) or "no evidence"
        lines.append(f"- **{claim.status}** — {claim.claim} ({paths})")
    lines += [
        "",
        "## Project Structure",
        "",
        f"- Package directories: {', '.join(report.project_structure.package_directories) or 'none'}",
        f"- Entrypoints: {', '.join(report.project_structure.entrypoints) or 'none'}",
        f"- Dependency files: {', '.join(report.project_structure.dependency_files) or 'none'}",
        f"- Test files: {len(report.project_structure.test_files)}",
        f"- Largest module: {report.project_structure.max_module_lines} lines",
    ]
    lines += [f"- Note: {note}" for note in report.project_structure.architecture_notes]
    lines += ["", "## Engineering Checks", ""]
    lines += [f"- **{check.status}** — {check.name}: {check.message}" for check in report.engineering_checks]
    lines += ["", "## Security Findings", ""]
    if report.security_findings:
        lines += [
            f"- **{item.severity} / {item.rule_id}** — {item.path}:{item.line} — {item.title}"
            for item in report.security_findings
        ]
    else:
        lines.append("- No findings from the lightweight scanner.")
    lines += [
        "",
        "## Test Result",
        "",
        f"- Status: **{report.test_result.status}**",
        f"- Reason: {report.test_result.reason}",
        "",
        "## Conclusion",
        "",
        report.summary,
    ]
    if report.roast:
        lines += ["", "## Roast (evidence-based)", "", report.roast]
    lines += ["", "> Scanner results are indicators, not a replacement for a professional security review.", ""]
    return "\n".join(lines)
