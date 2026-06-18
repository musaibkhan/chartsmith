from fastapi import APIRouter, HTTPException, Query
from src.core.helm_client import list_charts

router = APIRouter()


@router.get("/charts")
async def get_charts(repo: str = Query(..., description="Repo name, e.g. 'grafana'")):
    try:
        rows = await list_charts(repo)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return [
        {
            "name": r.get("name"),
            "description": r.get("description", ""),
            "latest_version": r.get("version", ""),
        }
        for r in rows
    ]
