import re
from pathlib import Path

from app.schemas.audit import EngineeringCheck, Evidence
from app.tools.repository import evidence_for_file, iter_repository_files, safe_read


def _check(
    root: Path,
    check_id: str,
    name: str,
    candidates: list[str],
    max_bytes: int,
    *,
    missing: str,
) -> EngineeringCheck:
    for candidate in candidates:
        paths = list(root.glob(candidate))
        if paths:
            path = paths[0]
            return EngineeringCheck(
                id=check_id,
                name=name,
                status="pass",
                evidence=[evidence_for_file(root, path, f"Found {name}", max_bytes)],
                message=f"{name} detected.",
            )
    return EngineeringCheck(id=check_id, name=name, status="fail", message=missing)


def _config_check(
    root: Path,
    check_id: str,
    name: str,
    standalone: list[str],
    pyproject_pattern: str,
    max_bytes: int,
) -> EngineeringCheck:
    for candidate in standalone:
        path = root / candidate
        if path.exists():
            return EngineeringCheck(
                id=check_id,
                name=name,
                status="pass",
                evidence=[evidence_for_file(root, path, f"Found {name}", max_bytes)],
                message=f"{name} detected.",
            )
    pyproject = root / "pyproject.toml"
    content = safe_read(pyproject, root, max_bytes) if pyproject.exists() else ""
    if re.search(pyproject_pattern, content, re.IGNORECASE):
        return EngineeringCheck(
            id=check_id,
            name=name,
            status="pass",
            evidence=[evidence_for_file(root, pyproject, f"Found {name}", max_bytes)],
            message=f"{name} detected.",
        )
    return EngineeringCheck(
        id=check_id,
        name=name,
        status="fail",
        message=f"No {name.lower()} configuration found.",
    )


def _first_pattern_evidence(
    root: Path,
    files: list[Path],
    pattern: str,
    max_bytes: int,
    description: str,
) -> Evidence | None:
    compiled = re.compile(pattern, re.IGNORECASE)
    for path in files:
        content = safe_read(path, root, max_bytes)
        for line_number, line in enumerate(content.splitlines(), 1):
            if compiled.search(line):
                return Evidence(
                    type="code" if path.suffix == ".py" else "config",
                    path=path.relative_to(root).as_posix(),
                    line_start=line_number,
                    line_end=line_number,
                    excerpt=line.strip()[:500],
                    description=description,
                )
    return None


def _pattern_check(
    root: Path,
    files: list[Path],
    check_id: str,
    name: str,
    pattern: str,
    max_bytes: int,
    failure: str,
) -> EngineeringCheck:
    evidence = _first_pattern_evidence(root, files, pattern, max_bytes, f"Evidence for {name}")
    return EngineeringCheck(
        id=check_id,
        name=name,
        status="pass" if evidence else "fail",
        evidence=[evidence] if evidence else [],
        message=f"{name} detected." if evidence else failure,
    )


def _readme_command_check(root: Path, max_bytes: int) -> EngineeringCheck:
    readmes = sorted(root.glob("README*"))
    if not readmes:
        return EngineeringCheck(
            id="readme_commands",
            name="README startup commands match repository",
            status="unknown",
            message="README is missing, so startup commands cannot be checked.",
        )
    readme = readmes[0]
    content = safe_read(readme, root, max_bytes)
    commands = re.findall(
        r"(?m)^\s*(?:\$ )?(python\s+-m\s+[\w.]+|uvicorn\s+[\w.]+:[\w]+|"
        r"python\s+[\w./-]+\.py|(?:uv|poetry)\s+run\s+[\w.-]+)",
        content,
    )
    if not commands:
        return EngineeringCheck(
            id="readme_commands",
            name="README startup commands match repository",
            status="warn",
            message="No recognizable Python startup command was found in README.",
        )
    missing: list[str] = []
    for command in commands:
        if command.startswith("python -m "):
            module = command.removeprefix("python -m ").strip().replace(".", "/")
            if not (root / f"{module}.py").exists() and not (root / module / "__main__.py").exists():
                missing.append(command)
        elif command.startswith("uvicorn "):
            module = command.split()[1].split(":", 1)[0].replace(".", "/")
            if not (root / f"{module}.py").exists():
                missing.append(command)
        elif command.startswith("python ") and command.endswith(".py"):
            target = command.split(maxsplit=1)[1]
            if not (root / target).exists():
                missing.append(command)
    excerpt = "\n".join(commands[:8])
    evidence = Evidence(
        type="config",
        path=readme.relative_to(root).as_posix(),
        line_start=1,
        line_end=min(200, len(content.splitlines())),
        excerpt=excerpt[:900],
        description="Recognized startup commands from README",
    )
    return EngineeringCheck(
        id="readme_commands",
        name="README startup commands match repository",
        status="fail" if missing else "pass",
        evidence=[evidence],
        message=(
            f"Commands with no matching entrypoint: {', '.join(missing)}"
            if missing
            else "Recognized README startup commands match repository entrypoints."
        ),
    )


def inspect_engineering(root: Path, max_bytes: int) -> list[EngineeringCheck]:
    checks = [
        _check(root, "readme", "README", ["README*", "readme*"], max_bytes, missing="README is missing."),
        _check(root, "license", "License", ["LICENSE*", "COPYING*"], max_bytes, missing="License is missing."),
        _check(root, "tests", "Test suite", ["tests", "test"], max_bytes, missing="No test directory found."),
        _check(root, "dockerfile", "Dockerfile", ["Dockerfile", "*/Dockerfile"], max_bytes, missing="Dockerfile is missing."),
        _check(root, "compose", "Docker Compose", ["docker-compose.yml", "compose.yml", "compose.yaml"], max_bytes, missing="Compose configuration is missing."),
        _check(root, "env_example", "Environment example", [".env.example", ".env.sample"], max_bytes, missing="No environment template found."),
        _check(root, "ci", "CI workflow", [".github/workflows/*.yml", ".github/workflows/*.yaml"], max_bytes, missing="No CI workflow found."),
        _config_check(
            root,
            "typing",
            "Type checking",
            ["mypy.ini", "pyrightconfig.json"],
            r"\[tool\.(?:mypy|pyright)\]",
            max_bytes,
        ),
        _config_check(
            root,
            "formatting",
            "Formatting/linting",
            ["ruff.toml", ".ruff.toml"],
            r"\[tool\.(?:ruff|black|isort)\]",
            max_bytes,
        ),
    ]
    files = iter_repository_files(root)
    code_and_config = [
        path
        for path in files
        if path.suffix in {".py", ".toml", ".yml", ".yaml", ".txt", ".cfg", ".ini", ".sh"}
        and path.stat().st_size <= max_bytes
    ]
    env_files = [path for path in files if path.name == ".env"]
    checks.append(
        EngineeringCheck(
            id="committed_env",
            name="No committed .env",
            status="fail" if env_files else "pass",
            evidence=[
                evidence_for_file(root, path, "Potential committed environment file", max_bytes)
                for path in env_files[:5]
            ],
            message=(
                f"Found {len(env_files)} committed .env file(s)."
                if env_files
                else "No committed .env file detected."
            ),
        )
    )
    test_evidence = _first_pattern_evidence(
        root,
        code_and_config,
        r"(?m)^(?:\s*(?:async\s+)?def\s+test_|\s*class\s+Test\w+)",
        max_bytes,
        "Executable pytest-style test detected",
    )
    checks.append(
        EngineeringCheck(
            id="executable_tests",
            name="Executable tests",
            status="pass" if test_evidence else "fail",
            evidence=[test_evidence] if test_evidence else [],
            message="pytest-style tests detected." if test_evidence else "No executable pytest-style tests found.",
        )
    )
    checks.extend(
        [
            _pattern_check(
                root,
                code_and_config,
                "logging",
                "Structured/application logging",
                r"\b(?:logging|getLogger|structlog)\b",
                max_bytes,
                "No logging implementation found.",
            ),
            _pattern_check(
                root,
                code_and_config,
                "exceptions",
                "Exception handling",
                r"\btry\s*:|\bexcept(?:\s+\w+|\s*\()",
                max_bytes,
                "No exception handling found.",
            ),
            _pattern_check(
                root,
                code_and_config,
                "health",
                "Health check",
                r"[/\"']health\b|healthcheck",
                max_bytes,
                "No health check found.",
            ),
        ]
    )
    lock_files = [root / name for name in ("uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock")]
    requirements = [path for path in files if path.name.startswith("requirements") and path.suffix == ".txt"]
    constrained_requirement = _first_pattern_evidence(
        root,
        requirements,
        r"^[A-Za-z0-9_.-]+(?:\[[^\]]+\])?(?:==|~=|>=.+,<)",
        max_bytes,
        "Constrained dependency declaration",
    )
    existing_lock = next((path for path in lock_files if path.exists()), None)
    checks.append(
        EngineeringCheck(
            id="pinned",
            name="Dependency constraints",
            status="pass" if existing_lock or constrained_requirement else "fail",
            evidence=(
                [evidence_for_file(root, existing_lock, "Dependency lock file", max_bytes)]
                if existing_lock
                else [constrained_requirement] if constrained_requirement else []
            ),
            message=(
                "Dependency lock or constrained requirements detected."
                if existing_lock or constrained_requirement
                else "Dependencies do not appear locked or constrained."
            ),
        )
    )
    hardcoded_path = _first_pattern_evidence(
        root,
        code_and_config,
        r"(?:/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)",
        max_bytes,
        "Machine-specific absolute path",
    )
    checks.append(
        EngineeringCheck(
            id="hardcoded_paths",
            name="No hardcoded machine paths",
            status="fail" if hardcoded_path else "pass",
            evidence=[hardcoded_path] if hardcoded_path else [],
            message=(
                "A machine-specific absolute path was detected."
                if hardcoded_path
                else "No obvious machine-specific path detected."
            ),
        )
    )
    hardcoded_secret = _first_pattern_evidence(
        root,
        code_and_config,
        r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{12,}['\"]",
        max_bytes,
        "Possible hardcoded credential",
    )
    if hardcoded_secret:
        hardcoded_secret.excerpt = re.sub(
            r"(['\"])[A-Za-z0-9_./+=-]{12,}\1",
            r"\1***REDACTED***\1",
            hardcoded_secret.excerpt,
        )
    checks.append(
        EngineeringCheck(
            id="hardcoded_secrets",
            name="No hardcoded secrets",
            status="fail" if hardcoded_secret else "pass",
            evidence=[hardcoded_secret] if hardcoded_secret else [],
            message=(
                "A possible hardcoded credential was detected."
                if hardcoded_secret
                else "No obvious hardcoded credential detected."
            ),
        )
    )
    checks.append(_readme_command_check(root, max_bytes))
    capability_patterns = [
        (
            "model_api_usage",
            "Model API integration",
            r"\b(?:openai|anthropic|chat\.completions|responses\.create|LLM_BASE_URL)\b",
            "No model API integration detected.",
        ),
        (
            "tool_orchestration",
            "Tool or agent orchestration",
            r"\b(?:StateGraph|add_node|tool_call|register_tool|BaseTool|@tool)\b",
            "No tool or agent orchestration detected.",
        ),
        (
            "data_processing",
            "Data processing pipeline",
            r"\b(?:pandas|polars|numpy|transform|pipeline|chunk|embedding|vector)\b",
            "No substantial data processing pipeline detected.",
        ),
        (
            "state_management",
            "State management",
            r"\b(?:TypedDict|BaseModel|Session|mapped_column|state\[|StateGraph)\b",
            "No explicit state management detected.",
        ),
        (
            "evaluation_system",
            "Evaluation or scoring system",
            r"\b(?:evaluate|evaluation|metric|score|benchmark|assert)\b",
            "No evaluation or scoring system detected.",
        ),
    ]
    checks.extend(
        _pattern_check(root, code_and_config, check_id, name, pattern, max_bytes, failure)
        for check_id, name, pattern, failure in capability_patterns
    )
    content = "\n".join(safe_read(path, root, max_bytes) for path in code_and_config)
    todo_count = len(re.findall(r"(?m)\b(TODO|FIXME)\b|^\s*pass\s*(?:#.*)?$", content))
    checks.append(
        EngineeringCheck(
            id="empty_implementations",
            name="No excessive empty implementations",
            status="warn" if todo_count > 10 else "pass",
            message=f"Found {todo_count} TODO/FIXME/pass markers.",
        )
    )
    return checks
