import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.schemas.audit import SecurityFinding
from app.tools.repository import iter_repository_files, safe_read


@dataclass(frozen=True)
class SecurityRule:
    rule_id: str
    title: str
    pattern: re.Pattern[str]
    severity: Literal["low", "medium", "high", "critical"]
    recommendation: str
    secret: bool = False


RULES = [
    SecurityRule("SEC001", "Possible API key", re.compile(r"(?i)(api[_-]?key|token)\s*[:=]\s*['\"]([A-Za-z0-9_\-]{16,})"), "high", "Move secrets to environment variables and rotate exposed values.", True),
    SecurityRule("SEC002", "Private key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "critical", "Remove and rotate the private key immediately.", True),
    SecurityRule("SEC003", "Dynamic eval", re.compile(r"\beval\s*\("), "high", "Replace eval with explicit parsing."),
    SecurityRule("SEC004", "Dynamic exec", re.compile(r"\bexec\s*\("), "high", "Avoid executing dynamic code."),
    SecurityRule("SEC005", "Shell execution enabled", re.compile(r"shell\s*=\s*True"), "high", "Pass an argument array and keep shell disabled."),
    SecurityRule("SEC006", "os.system call", re.compile(r"\bos\.system\s*\("), "high", "Use subprocess with an argument array and validation."),
    SecurityRule("SEC007", "Unsafe pickle load", re.compile(r"\bpickle\.loads?\s*\("), "high", "Use a safe serialization format for untrusted data."),
    SecurityRule("SEC008", "World-writable permissions", re.compile(r"chmod\s+(?:-R\s+)?777"), "medium", "Use least-privilege file permissions."),
    SecurityRule("SEC009", "Curl piped to shell", re.compile(r"curl[^|\n]*\|\s*(?:sh|bash)"), "high", "Download, verify, then execute installers separately."),
    SecurityRule("SEC010", "Overly broad CORS", re.compile(r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]"), "medium", "Restrict CORS to trusted origins."),
    SecurityRule("SEC011", "Debug enabled by default", re.compile(r"debug\s*=\s*True"), "medium", "Disable debug mode by default."),
    SecurityRule("SEC012", "Possible weak default password", re.compile(r"(?i)password\s*[:=]\s*['\"](?:password|admin|123456)['\"]"), "high", "Require a strong secret through configuration.", True),
    SecurityRule(
        "SEC013",
        "Possible hardcoded database password",
        re.compile(r"(?i)(?:db|database)[_-]?password\s*[:=]\s*['\"]([^'\"]{8,})['\"]"),
        "high",
        "Load database credentials from a secret store or environment variable.",
        True,
    ),
    SecurityRule(
        "SEC014",
        "Subprocess invoked with a command string",
        re.compile(r"\bsubprocess\.(?:run|call|Popen|check_output)\s*\(\s*[furb]*['\"]"),
        "medium",
        "Prefer a validated argument array and keep shell execution disabled.",
    ),
    SecurityRule(
        "SEC015",
        "World-writable Python chmod",
        re.compile(r"\bos\.chmod\s*\([^,\n]+,\s*(?:0o777|511)\s*\)"),
        "medium",
        "Use least-privilege file permissions.",
    ),
    SecurityRule(
        "SEC016",
        "Database URL contains inline credentials",
        re.compile(r"(?i)(?:postgres(?:ql)?|mysql|mariadb|mongodb)://[^:\s/]+:[^@\s/]+@"),
        "high",
        "Move database credentials to a secret store and rotate exposed credentials.",
        True,
    ),
]


def redact(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def _redact_line(line: str) -> str:
    result = line
    for pattern in [
        re.compile(r"(?i)((?:api[_-]?key|token|password)\s*[:=]\s*['\"])([^'\"]+)(['\"])"),
        re.compile(r"(?i)(://[^:\s/]+:)([^@\s/]+)(@)"),
    ]:
        result = pattern.sub(lambda match: f"{match.group(1)}{redact(match.group(2))}{match.group(3)}", result)
    if "PRIVATE KEY" in result:
        return "[REDACTED PRIVATE KEY MATERIAL]"
    return result[:500]


def scan_security(root: Path, max_bytes: int) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    allowed = {
        ".py",
        ".toml",
        ".yml",
        ".yaml",
        ".json",
        ".sh",
        ".md",
        ".txt",
        ".ini",
        ".cfg",
        ".pem",
        ".key",
    }
    for path in iter_repository_files(root):
        if (
            path.suffix.lower() not in allowed
            and path.name not in {".env", "Dockerfile", "Containerfile"}
        ) or path.stat().st_size > max_bytes:
            continue
        content = safe_read(path, root, max_bytes)
        for number, line in enumerate(content.splitlines(), 1):
            for rule in RULES:
                if rule.pattern.search(line):
                    findings.append(
                        SecurityFinding(
                            rule_id=rule.rule_id,
                            title=rule.title,
                            severity=rule.severity,
                            path=path.relative_to(root).as_posix(),
                            line=number,
                            excerpt=_redact_line(line.strip()),
                            recommendation=rule.recommendation,
                        )
                    )
    return findings[:100]
