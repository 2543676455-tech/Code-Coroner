import re
from pathlib import Path

from app.schemas.audit import Claim, Evidence
from app.tools.repository import evidence_for_file, iter_repository_files, safe_read

CLAIM_PATTERNS: list[tuple[str, str, list[str], tuple[str, ...]]] = [
    ("deployment", "支持 Docker 一键部署", ["存在 Dockerfile", "存在 compose 配置", "存在启动命令"], ("docker", "容器", "一键部署")),
    ("testing", "包含完整测试", ["存在测试目录", "存在 pytest 配置", "测试可执行"], ("完整测试", "test suite", "pytest")),
    ("authentication", "支持身份认证", ["存在认证模块", "存在令牌或会话验证"], ("身份认证", "authentication", "oauth", "jwt")),
    ("streaming", "支持流式输出", ["存在流式响应实现"], ("流式", "streaming", "stream output")),
    ("retrieval", "支持向量检索", ["存在向量数据库或 embedding 实现"], ("向量检索", "vector search", "embedding")),
    ("database", "支持数据库持久化", ["存在数据库依赖", "存在模型或迁移"], ("数据库", "database", "sqlite", "postgres")),
    ("async", "支持异步任务", ["存在异步函数或任务队列"], ("异步任务", "background task", "celery")),
    ("agents", "支持多 Agent", ["存在多个 Agent 定义或编排图"], ("多 agent", "multi-agent", "multi agent")),
    ("production", "支持生产环境", ["存在部署配置", "存在日志和健康检查"], ("生产环境", "production-ready", "production ready")),
]


def extract_claims(readme: str) -> list[Claim]:
    lowered = readme.lower()
    lines = readme.splitlines()
    claims: list[Claim] = []
    for category, canonical, rules, keywords in CLAIM_PATTERNS:
        if any(keyword.lower() in lowered for keyword in keywords):
            matching_line = next(
                (
                    line
                    for line in lines
                    if any(keyword.lower() in line.lower() for keyword in keywords)
                ),
                "",
            )
            normalized = re.sub(r"^[#>*\-\d.\s]+", "", matching_line).strip()
            claim_text = normalized[:240] if 4 <= len(normalized) <= 240 else canonical
            claims.append(
                Claim(
                    id=f"claim_{len(claims) + 1:03d}",
                    claim=claim_text,
                    category=category,
                    verification_rules=rules,
                )
            )
    return claims


def _matching_evidence(root: Path, patterns: tuple[str, ...], max_bytes: int) -> list[Evidence]:
    evidence: list[Evidence] = []
    for path in iter_repository_files(root):
        if len(evidence) >= 4 or path.suffix.lower() not in {".py", ".toml", ".yml", ".yaml", ".json", ".cfg", ".ini"}:
            continue
        content = safe_read(path, root, max_bytes)
        for number, line in enumerate(content.splitlines(), 1):
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
                evidence.append(
                    Evidence(
                        type="code" if path.suffix == ".py" else "config",
                        path=path.relative_to(root).as_posix(),
                        line_start=number,
                        line_end=number,
                        excerpt=line.strip()[:500],
                        description="Rule-based match supporting the README claim",
                    )
                )
                break
    return evidence


def verify_claims(claims: list[Claim], root: Path, max_bytes: int) -> list[Claim]:
    rules: dict[str, tuple[str, ...]] = {
        "deployment": (r"FROM\s+python", r"docker compose", r"uvicorn|gunicorn"),
        "testing": (r"pytest", r"def test_", r"\[tool\.pytest"),
        "authentication": (r"oauth", r"jwt", r"authorization", r"authenticate"),
        "streaming": (r"StreamingResponse", r"stream=True", r"yield\s+"),
        "retrieval": (r"embedding", r"vector", r"chroma", r"faiss"),
        "database": (r"sqlalchemy", r"sqlite", r"postgres", r"mapped_column"),
        "async": (r"async def", r"BackgroundTasks", r"celery"),
        "agents": (r"StateGraph", r"agent", r"langgraph"),
        "production": (r"health", r"structlog", r"docker", r"github/workflows"),
    }
    for claim in claims:
        evidence = _matching_evidence(root, rules.get(claim.category, ()), max_bytes)
        if claim.category == "deployment":
            for name in ("Dockerfile", "docker-compose.yml", "compose.yml", "compose.yaml"):
                path = root / name
                if path.exists():
                    evidence.append(
                        evidence_for_file(root, path, f"Deployment artifact: {name}", max_bytes)
                    )
        elif claim.category == "testing":
            test_files = [
                path
                for path in iter_repository_files(root)
                if path.suffix == ".py"
                and (path.name.startswith("test_") or "tests" in path.relative_to(root).parts)
            ]
            for path in test_files[:2]:
                evidence.append(evidence_for_file(root, path, "Executable test artifact", max_bytes))
        unique: dict[tuple[str, int | None], Evidence] = {}
        for item in evidence:
            unique[(item.path, item.line_start)] = item
        evidence = list(unique.values())[:4]
        claim.evidence = evidence
        evidence_paths = {item.path for item in evidence}
        if claim.category == "deployment":
            has_dockerfile = "Dockerfile" in evidence_paths
            has_compose = any(
                path in evidence_paths
                for path in ("docker-compose.yml", "compose.yml", "compose.yaml")
            )
            has_startup = any(
                re.search(r"\b(?:CMD|ENTRYPOINT|uvicorn|gunicorn)\b", item.excerpt, re.IGNORECASE)
                for item in evidence
            )
            if has_dockerfile and (has_compose or has_startup):
                claim.status, claim.confidence = "verified", 0.9
                claim.reason = "Docker image configuration and a runnable startup path were found."
            elif evidence:
                claim.status, claim.confidence = "partial", 0.55
                claim.reason = "Some Docker artifacts exist, but one-click deployment is incomplete."
            else:
                claim.status, claim.confidence = "unsupported", 0.8
                claim.reason = "No Docker deployment artifact was found."
        elif claim.category == "testing":
            has_test = any(
                item.path.startswith("tests/")
                or Path(item.path).name.startswith("test_")
                or "def test_" in item.excerpt
                for item in evidence
            )
            has_pytest_config = any(
                item.path in {"pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml"}
                and "pytest" in item.excerpt.lower()
                for item in evidence
            )
            if has_test and has_pytest_config:
                claim.status, claim.confidence = "verified", 0.9
                claim.reason = "Executable tests and pytest configuration were found."
            elif evidence:
                claim.status, claim.confidence = "partial", 0.55
                claim.reason = "Test-related artifacts exist, but completeness is not demonstrated."
            else:
                claim.status, claim.confidence = "unsupported", 0.8
                claim.reason = "No test implementation or pytest configuration was found."
        elif len(evidence) >= 2:
            claim.status, claim.confidence = "verified", min(0.95, 0.65 + len(evidence) * 0.08)
            claim.reason = "Multiple repository artifacts support this claim."
        elif evidence:
            claim.status, claim.confidence = "partial", 0.55
            claim.reason = "Some implementation evidence exists, but the full claim is not demonstrated."
        else:
            claim.status, claim.confidence = "unsupported", 0.8
            claim.reason = "No supporting code or configuration was found by deterministic rules."
    return claims
