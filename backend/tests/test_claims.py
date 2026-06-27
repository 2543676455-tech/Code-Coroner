from pathlib import Path

from app.scanners.claims import extract_claims, verify_claims

FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def test_extracts_readme_claims() -> None:
    claims = extract_claims((FIXTURE / "README.md").read_text())
    assert {claim.category for claim in claims} >= {
        "deployment",
        "testing",
        "authentication",
        "streaming",
        "database",
    }


def test_verifies_claims_with_repository_evidence() -> None:
    claims = extract_claims((FIXTURE / "README.md").read_text())
    verified = verify_claims(claims, FIXTURE, 100_000)
    assert any(claim.status == "verified" for claim in verified)
    assert all(len(item.excerpt) <= 1000 for claim in verified for item in claim.evidence)
    assert all(not item.path.lower().startswith("readme") for claim in verified for item in claim.evidence)
