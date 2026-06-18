from fastapi import APIRouter, HTTPException
from src.core.helm_client import list_versions

router = APIRouter()


@router.get("/charts/{repo}/{name}/versions")
async def get_versions(repo: str, name: str):
    chart = f"{repo}/{name}"
    try:
        versions = await list_versions(chart)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return {"chart": chart, "versions": versions}
