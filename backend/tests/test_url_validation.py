import pytest
from app.tools.repository import validate_github_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/openai/openai-python", "https://github.com/openai/openai-python"),
        ("https://github.com/openai/openai-python.git", "https://github.com/openai/openai-python"),
    ],
)
def test_valid_github_urls(url: str, expected: str) -> None:
    assert validate_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/repo",
        "http://github.com/a/b",
        "https://gitlab.com/a/b",
        "https://github.com/a/b;rm",
        "https://github.com/a/b?x=1",
        "/tmp/repo",
    ],
)
def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_github_url(url)
