"""ChartSmith backend entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import repos, charts, versions, analyze
from src.core.helm_client import ensure_helm_ready


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify helm CLI is installed and cache dir exists.
    await ensure_helm_ready()
    yield


app = FastAPI(
    title="ChartSmith",
    description="Forecast every breaking change before you upgrade a Helm chart.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(repos.router,    prefix=API_PREFIX, tags=["repos"])
app.include_router(charts.router,   prefix=API_PREFIX, tags=["charts"])
app.include_router(versions.router, prefix=API_PREFIX, tags=["versions"])
app.include_router(analyze.router,  prefix=API_PREFIX, tags=["analyze"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "chartsmith"}
