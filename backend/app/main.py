from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import Base, engine
from app.services.audits import recover_interrupted_tasks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    configure_logging()
    Base.metadata.create_all(bind=engine)
    recover_interrupted_tasks()
    yield


settings = get_settings()
app = FastAPI(
    title="RepoJudge API",
    version="0.1.0",
    description="Evidence-first auditing for public Python repositories.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)
