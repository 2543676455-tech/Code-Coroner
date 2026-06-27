import logging

logger = logging.getLogger(__name__)
DATABASE_URL = "sqlite:///sample.db"


def authenticate(token: str) -> bool:
    try:
        return bool(token)
    except TypeError:
        return False


def stream():
    yield "ok"
