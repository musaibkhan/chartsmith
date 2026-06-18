"""Pull GitHub release notes between two chart versions."""
from __future__ import annotations
import os
import httpx

GITHUB = "https://api.github.com"


async def fetch_releases(owner: str, repo: str, chart_filter: str | None = None) -> list[dict]:
    """Fetch up to 100 latest releases. If chart_filter given, only return tags
    matching that chart (Grafana mono-repo style: 'loki-6.46.0', 'grafana-8.0.0').
    """
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.get(f"{GITHUB}/repos/{owner}/{repo}/releases?per_page=100", headers=headers)
        r.raise_for_status()
        releases = r.json()
    if chart_filter:
        releases = [x for x in releases if chart_filter in (x.get("tag_name") or "")]
    return releases


def extract_breaking(release_body: str) -> list[str]:
    """Grep for breaking-change bullets in a release body."""
    if not release_body:
        return []
    bullets, in_section = [], False
    for line in release_body.splitlines():
        lower = line.lower()
        if any(k in lower for k in ("breaking change", "breaking-change", "⚠️", "deprecat")):
            in_section = True
            continue
        if in_section:
            if line.startswith("- ") or line.startswith("* "):
                bullets.append(line.lstrip("-* ").strip())
            elif line.strip().startswith("#"):
                in_section = False
    return bullets
