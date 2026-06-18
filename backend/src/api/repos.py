from fastapi import APIRouter, HTTPException
from src.models.report import RepoIn
from src.core.helm_client import repo_add

router = APIRouter()


@router.post("/repos/index")
async def index_repo(repo: RepoIn):
    try:
        await repo_add(repo.name, repo.url)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return {"name": repo.name, "url": repo.url, "status": "indexed"}
