from pathlib import Path

from app.scanners.security import redact, scan_security


def test_secret_redaction() -> None:
    assert redact("abcdefghijklmnop") == "abc...nop"
    assert redact("short") == "***"


def test_security_rules_and_redacted_evidence(tmp_path: Path) -> None:
    source = tmp_path / "bad.py"
    source.write_text('api_key = "abcdefghijklmnop"\neval("1 + 1")\n', encoding="utf-8")
    findings = scan_security(tmp_path, 10_000)
    assert {item.rule_id for item in findings} == {"SEC001", "SEC003"}
    assert "abcdefghijklmnop" not in findings[0].excerpt


def test_scans_dotenv_and_redacts_database_password(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql://repojudge:supersecret@example.com/db\n",
        encoding="utf-8",
    )
    findings = scan_security(tmp_path, 10_000)
    database = next(item for item in findings if item.rule_id == "SEC016")
    assert "supersecret" not in database.excerpt
    assert "..." in database.excerpt
