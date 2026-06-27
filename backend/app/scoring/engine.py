from app.core.scoring_rules import (
    LEARNING_WEIGHTS,
    PRODUCTION_WEIGHTS,
    README_WEIGHTS,
    WRAPPER_WEIGHTS,
)
from app.schemas.audit import (
    Claim,
    EngineeringCheck,
    ProjectStructure,
    RepositoryMetadata,
    ScoreDetail,
    Scores,
    SecurityFinding,
    TestResult,
)


def _bounded(value: float) -> int:
    return max(0, min(100, round(value)))


def calculate_scores(
    metadata: RepositoryMetadata,
    structure: ProjectStructure,
    claims: list[Claim],
    checks: list[EngineeringCheck],
    findings: list[SecurityFinding],
    test_result: TestResult,
) -> Scores:
    check_map = {check.id: check for check in checks}
    additions: list[str] = []
    deductions: list[str] = []
    verified = sum(claim.status == "verified" for claim in claims)
    partial = sum(claim.status == "partial" for claim in claims)
    unsupported = sum(claim.status == "unsupported" for claim in claims)
    ratio = (verified + partial * 0.5) / len(claims) if claims else 0.0
    readme = ratio * README_WEIGHTS["verified_claim_ratio"]
    if check_map.get("readme") and check_map["readme"].status == "pass":
        readme += README_WEIGHTS["readme_present"]
        additions.append("README exists (+15)")
    if any(
        check_map.get(key) and check_map[key].status == "pass"
        for key in ("dockerfile", "readme_commands")
    ):
        readme += README_WEIGHTS["startup_artifacts"]
        additions.append("Runnable artifacts match documentation (+15)")
    penalty = min(README_WEIGHTS["unsupported_claim_penalty"], unsupported * 3)
    readme += 10 - penalty
    if penalty:
        deductions.append(f"Unsupported README claims (-{penalty})")
    if not claims:
        deductions.append("No verifiable README claims were detected")

    production = 0.0
    prod_add: list[str] = []
    prod_deduct: list[str] = []
    for key, weight in PRODUCTION_WEIGHTS.items():
        earned: float
        if key == "security":
            risk = sum({"low": 1, "medium": 3, "high": 7, "critical": 15}[item.severity] for item in findings)
            earned = max(0, weight - risk)
        elif key == "tests":
            present = check_map.get("tests") and check_map["tests"].status == "pass"
            earned = weight if test_result.status == "passed" else weight * 0.5 if present else 0
        else:
            earned = weight if check_map.get(key) and check_map[key].status == "pass" else 0
        production += earned
        (prod_add if earned else prod_deduct).append(
            f"{key}: +{round(earned)}" if earned else f"{key}: missing or failed"
        )

    learning = 0.0
    learn_add: list[str] = []
    learn_deduct: list[str] = []
    for key, weight in LEARNING_WEIGHTS.items():
        earned = 0.0
        if key == "modularity":
            if metadata.python_files >= 5 and structure.max_module_lines <= 800:
                earned = float(weight)
            elif metadata.python_files >= 2:
                earned = weight * 0.4
        elif key == "runnable":
            earned = weight if any(
                check_map.get(item) and check_map[item].status == "pass"
                for item in ("tests", "dockerfile")
            ) else 0
        else:
            earned = weight if check_map.get(key) and check_map[key].status == "pass" else 0
        learning += earned
        (learn_add if earned else learn_deduct).append(
            f"{key}: +{round(earned)}" if earned else f"{key}: no evidence"
        )

    wrapper = 0.0
    wrap_add: list[str] = []
    if metadata.lines_of_python < 500:
        wrapper += WRAPPER_WEIGHTS["small_codebase"]
        wrap_add.append(f"Small Python implementation (+{WRAPPER_WEIGHTS['small_codebase']})")
    if check_map.get("model_api_usage") and check_map["model_api_usage"].status == "pass":
        wrapper += WRAPPER_WEIGHTS["model_api_usage"]
        wrap_add.append(f"Model API integration is central (+{WRAPPER_WEIGHTS['model_api_usage']})")
    capability_penalties = [
        ("tool_orchestration", "missing_tools", "No real tool or agent orchestration"),
        ("data_processing", "missing_data_pipeline", "No substantial data processing pipeline"),
        ("state_management", "missing_state", "No explicit state management"),
        ("evaluation_system", "missing_evaluation", "No evaluation system"),
    ]
    for check_id, weight_key, message in capability_penalties:
        if not check_map.get(check_id) or check_map[check_id].status != "pass":
            wrapper += WRAPPER_WEIGHTS[weight_key]
            wrap_add.append(f"{message} (+{WRAPPER_WEIGHTS[weight_key]})")
    claim_gap = min(WRAPPER_WEIGHTS["claim_gap"], unsupported * 5)
    wrapper += claim_gap
    if unsupported:
        wrap_add.append(f"Claims exceed detected implementation (+{claim_gap})")

    return Scores(
        readme_credibility=ScoreDetail(score=_bounded(readme), additions=additions, deductions=deductions),
        production_readiness=ScoreDetail(score=_bounded(production), additions=prod_add, deductions=prod_deduct),
        learning_value=ScoreDetail(score=_bounded(learning), additions=learn_add, deductions=learn_deduct),
        wrapper_index=ScoreDetail(score=_bounded(wrapper), additions=wrap_add, deductions=[]),
    )
