import ast
from pathlib import Path

from app.schemas.audit import ModuleMetric, ProjectStructure
from app.tools.repository import iter_repository_files, safe_read

DEPENDENCY_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "pdm.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
    "setup.py",
    "setup.cfg",
}
CONFIGURATION_NAMES = {
    "pyproject.toml",
    "pytest.ini",
    "tox.ini",
    "mypy.ini",
    "ruff.toml",
    ".ruff.toml",
    ".pre-commit-config.yaml",
    ".env.example",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
    "compose.yaml",
}


def _is_entrypoint(path: Path, content: str) -> bool:
    if path.name in {"main.py", "__main__.py", "app.py", "cli.py", "manage.py"}:
        return True
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        left = node.test.left
        comparators = node.test.comparators
        if (
            isinstance(left, ast.Name)
            and left.id == "__name__"
            and comparators
            and isinstance(comparators[0], ast.Constant)
            and comparators[0].value == "__main__"
        ):
            return True
    return False


def _module_notes(path: Path, content: str) -> list[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    notes: list[str] = []
    classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    functions = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
    if classes:
        notes.append(f"{path.as_posix()} defines {classes} class(es).")
    if functions >= 10:
        notes.append(f"{path.as_posix()} contains {functions} functions and may deserve decomposition.")
    return notes


def analyze_structure(root: Path, max_bytes: int) -> ProjectStructure:
    files = iter_repository_files(root)
    relative_files = [path.relative_to(root) for path in files]
    top_level = sorted(path.name for path in root.iterdir() if not path.name.startswith(".git"))
    package_dirs = sorted(
        path.parent.relative_to(root).as_posix()
        for path in files
        if path.name == "__init__.py" and path.parent != root
    )
    dependency_files = sorted(
        path.as_posix()
        for path in relative_files
        if path.name in DEPENDENCY_NAMES or path.name.startswith("requirements")
    )
    configuration_files = sorted(
        path.as_posix()
        for path in relative_files
        if path.name in CONFIGURATION_NAMES or ".github/workflows" in path.as_posix()
    )
    test_files = sorted(
        path.as_posix()
        for path in relative_files
        if path.suffix == ".py"
        and (path.name.startswith("test_") or path.name.endswith("_test.py"))
    )
    entrypoints: list[str] = []
    metrics: list[ModuleMetric] = []
    notes: list[str] = []
    for path in files:
        if path.suffix != ".py":
            continue
        content = safe_read(path, root, max_bytes)
        relative = path.relative_to(root)
        if _is_entrypoint(path, content):
            entrypoints.append(relative.as_posix())
        line_count = len(content.splitlines())
        metrics.append(ModuleMetric(path=relative.as_posix(), lines=line_count))
        notes.extend(_module_notes(relative, content))
    metrics.sort(key=lambda item: item.lines, reverse=True)
    if not package_dirs:
        notes.append("No importable Python package directory was detected.")
    if metrics and metrics[0].lines > 800:
        notes.append(
            f"Largest module {metrics[0].path} has {metrics[0].lines} lines and is highly concentrated."
        )
    return ProjectStructure(
        top_level_entries=top_level[:100],
        package_directories=package_dirs[:100],
        entrypoints=sorted(entrypoints)[:100],
        dependency_files=dependency_files[:100],
        configuration_files=configuration_files[:100],
        test_files=test_files[:200],
        largest_modules=metrics[:10],
        max_module_lines=metrics[0].lines if metrics else 0,
        architecture_notes=notes[:30],
    )
