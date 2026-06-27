FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --no-cache-dir \
    "pytest>=8.3,<9" \
    "setuptools>=75,<81" \
    "wheel>=0.45,<1" \
    "uv>=0.11,<1" \
    && useradd --create-home --uid 65532 sandbox

USER sandbox
WORKDIR /workspace
ENTRYPOINT []
