from pathlib import Path

from app.agents.llm import OpenAICompatibleClient
from app.core.config import get_settings
from app.graph.nodes.common import record_error
from app.graph.state import RepoJudgeState
from app.scanners.claims import verify_claims as verify


def verify_claims(state: RepoJudgeState) -> dict[str, object]:
    try:
        settings = get_settings()
        claims = verify(
            state.get("claims", []),
            Path(state["repository_path"]),
            settings.max_file_bytes,
        )
        errors = state.get("errors", [])
        if settings.llm_enabled:
            try:
                client = OpenAICompatibleClient(settings)
                for claim in claims:
                    evidence = "\n".join(
                        f"{item.path}:{item.line_start or 1} {item.excerpt[:500]}"
                        for item in claim.evidence[:4]
                    )
                    explanation = client.explain(
                        f"Claim: {claim.claim}\nRule status: {claim.status}\nEvidence:\n"
                        f"{evidence or '[no evidence]'}"
                    )
                    claim.reason = f"{claim.reason} LLM evidence explanation: {explanation}"
            except Exception as exc:
                errors = record_error(state, "verify_claims_llm", exc)
        return {"claims": claims, "errors": errors, "current_stage": "verify_claims"}
    except Exception as exc:
        return {
            "errors": record_error(state, "verify_claims", exc),
            "current_stage": "verify_claims",
        }
