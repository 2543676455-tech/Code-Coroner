import shutil
import subprocess
import time
import uuid
from pathlib import Path

from app.core.config import Settings
from app.schemas.audit import TestResult
from app.tools.repository import iter_repository_files, safe_read


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        probe = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def _ensure_sandbox_image(settings: Settings) -> tuple[bool, str]:
    inspect = subprocess.run(
        ["docker", "image", "inspect", settings.sandbox_image],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if inspect.returncode == 0:
        return True, ""
    project_root = Path(__file__).resolve().parents[3]
    dockerfile = project_root / "backend" / "sandbox.Dockerfile"
    if not dockerfile.exists():
        return False, f"Sandbox image {settings.sandbox_image} is missing."
    try:
        build = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(dockerfile),
                "-t",
                settings.sandbox_image,
                str(project_root),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, "Trusted sandbox image build timed out."
    if build.returncode != 0:
        return False, f"Trusted sandbox image build failed: {build.stderr[-1000:]}"
    return True, ""


def _has_pytest_suite(root: Path) -> bool:
    files = iter_repository_files(root)
    has_test_file = any(
        path.suffix == ".py"
        and (path.name.startswith("test_") or path.name.endswith("_test.py") or "tests" in path.parts)
        for path in files
    )
    has_config = (root / "pytest.ini").exists()
    config_patterns = {
        "pyproject.toml": "[tool.pytest",
        "setup.cfg": "[tool:pytest]",
        "tox.ini": "[pytest]",
    }
    for name, marker in config_patterns.items():
        path = root / name
        if path.exists() and marker in safe_read(path, root, 524_288):
            has_config = True
    return has_test_file and has_config


def run_tests_in_sandbox(root: Path, settings: Settings) -> TestResult:
    if not _docker_available():
        return TestResult(status="skipped", reason="Docker daemon is unavailable.")
    if not _has_pytest_suite(root):
        return TestResult(
            status="skipped",
            reason="No pytest test files and configuration were detected.",
        )
    image_ready, image_error = _ensure_sandbox_image(settings)
    if not image_ready:
        return TestResult(status="skipped", reason=image_error)
    started = time.monotonic()
    container_name = f"repojudge-test-{uuid.uuid4().hex[:12]}"
    command = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--network",
        "none",
        "--cpus",
        "1",
        "--memory",
        "1g",
        "--pids-limit",
        "256",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=256m",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--user",
        "65532:65532",
        "-e",
        "HOME=/tmp",
        "-e",
        "PIP_NO_CACHE_DIR=1",
        "-v",
        f"{root.resolve()}:/workspace:ro",
        "-w",
        "/workspace",
        settings.sandbox_image,
        "sh",
        "-c",
        (
            "cp -a /workspace /tmp/repo && cd /tmp/repo && "
            "python -m venv --system-site-packages /tmp/venv && . /tmp/venv/bin/activate && "
            "if [ -f requirements.txt ]; then "
            "python -m pip install --no-index -r requirements.txt; fi && "
            "if [ -f pyproject.toml ] || [ -f setup.py ]; then "
            "python -m pip install --no-index --no-build-isolation -e .; fi && "
            "python -m pytest -q"
        ),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.sandbox_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        log = (stdout + "\n" + stderr)[-8000:]
        return TestResult(
            status="timeout",
            duration_seconds=time.monotonic() - started,
            log=log,
            reason="Sandbox test execution timed out.",
        )
    log = (result.stdout + "\n" + result.stderr)[-8000:]
    return TestResult(
        status="passed" if result.returncode == 0 else "failed",
        exit_code=result.returncode,
        duration_seconds=time.monotonic() - started,
        log=log,
        reason="Tests executed in a restricted Docker container.",
    )
