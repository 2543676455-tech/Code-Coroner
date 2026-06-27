from pathlib import Path

from app.scanners.engineering import inspect_engineering
from app.scanners.structure import analyze_structure

FIXTURE = Path(__file__).parent / "fixtures" / "sample_repo"


def test_structure_analysis_finds_entrypoints_tests_and_modules() -> None:
    structure = analyze_structure(FIXTURE, 100_000)
    assert "pyproject.toml" in structure.dependency_files
    assert "tests/test_sample.py" in structure.test_files
    assert structure.largest_modules
    assert structure.max_module_lines >= 1
    assert "tests/__init__.py" not in structure.test_files


def test_name_string_is_not_mistaken_for_entrypoint(tmp_path: Path) -> None:
    source = tmp_path / "test_example.py"
    source.write_text('assert __name__ == "test_example"\n', encoding="utf-8")
    structure = analyze_structure(tmp_path, 100_000)
    assert structure.entrypoints == []


def test_engineering_check_set_is_structured_and_complete() -> None:
    checks = inspect_engineering(FIXTURE, 100_000)
    check_ids = {check.id for check in checks}
    assert {
        "executable_tests",
        "hardcoded_paths",
        "hardcoded_secrets",
        "readme_commands",
        "logging",
        "exceptions",
        "pinned",
    } <= check_ids
    assert all(check.message for check in checks)


def test_readme_command_mismatch_is_reported(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("```bash\npython missing.py\n```\n", encoding="utf-8")
    checks = {check.id: check for check in inspect_engineering(tmp_path, 100_000)}
    assert checks["readme_commands"].status == "fail"
    assert "missing.py" in checks["readme_commands"].message
