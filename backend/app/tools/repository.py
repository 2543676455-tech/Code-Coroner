import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from git import Repo

from app.core.config import Settings
from app.schemas.audit import Evidence, RepositoryMetadata

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}
GITHUB_PATH = re.compile(r"^/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?$")


def validate_github_url(url: str) -> str:
    if len(url) > 500 or any(char in url for char in "\r\n\t ;|&`$(){}[]<>"):
        raise ValueError("Repository URL contains forbidden characters")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ValueError("Only public https://github.com/owner/repo URLs are accepted")
    if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        raise ValueError("Credentials, ports, query strings, and fragments are not allowed")
    if not GITHUB_PATH.fullmatch(parsed.path):
        raise ValueError("GitHub URL must identify exactly one owner/repository")
    return f"https://github.com{parsed.path.removesuffix('/').removesuffix('.git')}"


def clone_repository(url: str, destination: Path, settings: Settings, token: str | None = None) -> Path:
    safe_url = validate_github_url(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    if token:
        environment.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.https://github.com/.extraHeader",
                "GIT_CONFIG_VALUE_0": f"Authorization: Bearer {token}",
            }
        )
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", safe_url, str(destination)],
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.clone_timeout_seconds,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError("Repository clone timed out") from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(destination, ignore_errors=True)
        detail = exc.stderr.strip()[-500:]
        raise RuntimeError(f"Repository clone failed: {detail}") from exc
    files = iter_repository_files(destination)
    if len(files) > settings.max_repository_files:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError(f"Repository exceeds {settings.max_repository_files} file limit")
    if sum(path.stat().st_size for path in files if path.exists()) > settings.max_repository_mb * 1024 * 1024:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError(f"Repository exceeds {settings.max_repository_mb} MB limit")
    return destination


def iter_repository_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
        for name in names:
            path = Path(current) / name
            if not path.is_symlink():
                files.append(path)
    return files


def directory_size(root: Path) -> int:
    return sum(path.stat().st_size for path in iter_repository_files(root) if path.exists())


def safe_read(path: Path, root: Path, max_bytes: int) -> str:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved_root not in resolved.parents and resolved != resolved_root:
        raise ValueError("Path traversal blocked")
    if not path.is_file() or path.stat().st_size > max_bytes:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def find_readme(root: Path) -> Path | None:
    candidates = sorted(root.glob("README*"))
    return next((path for path in candidates if path.is_file()), None)


def evidence_for_file(root: Path, path: Path, description: str, max_bytes: int) -> Evidence:
    content = safe_read(path, root, max_bytes)
    excerpt = "\n".join(content.splitlines()[:20])[:900]
    return Evidence(
        type="file",
        path=path.relative_to(root).as_posix(),
        line_start=1 if excerpt else None,
        line_end=min(20, len(content.splitlines())) if excerpt else None,
        excerpt=excerpt,
        description=description,
    )


def collect_metadata(root: Path, url: str) -> RepositoryMetadata:
    files = iter_repository_files(root)
    python_files = [path for path in files if path.suffix == ".py"]
    lines = 0
    for path in python_files:
        if path.stat().st_size <= 524_288:
            lines += len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    parts = url.rstrip("/").split("/")
    branch = ""
    sha = ""
    try:
        repo = Repo(root)
        branch = repo.active_branch.name
        sha = repo.head.commit.hexsha
    except Exception:
        pass
    return RepositoryMetadata(
        name=parts[-1],
        owner=parts[-2],
        url=url,
        default_branch=branch,
        commit_sha=sha,
        file_count=len(files),
        total_bytes=sum(path.stat().st_size for path in files),
        python_files=len(python_files),
        lines_of_python=lines,
    )
