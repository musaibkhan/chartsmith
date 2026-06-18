from __future__ import annotations
import asyncio, json, os, shutil
from pathlib import Path

HELM_CACHE = Path(os.getenv("HELM_CACHE_DIR", "/var/cache/helm"))


async def _run(*cmd: str) -> tuple[int, str, str]:
    p = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await p.communicate()
    return p.returncode or 0, out.decode(), err.decode()


async def ensure_helm_ready() -> None:
    if not shutil.which("helm"):
        raise RuntimeError("helm CLI not found in PATH")
    HELM_CACHE.mkdir(parents=True, exist_ok=True)


async def repo_add(name: str, url: str) -> None:
    code, _, err = await _run("helm", "repo", "add", name, url, "--force-update")
    if code != 0:
        raise RuntimeError(err)
    await _run("helm", "repo", "update", name)


async def list_charts(repo: str) -> list[dict]:
    code, out, err = await _run("helm", "search", "repo", repo, "-o", "json")
    if code != 0:
        raise RuntimeError(err)
    return json.loads(out or "[]")


async def list_versions(chart: str) -> list[str]:
    code, out, err = await _run(
        "helm", "search", "repo", chart, "--versions", "-o", "json"
    )
    if code != 0:
        raise RuntimeError(err)
    return [r["version"] for r in json.loads(out or "[]") if r.get("name") == chart]


def _find_chart_dir(dest: Path) -> Path | None:
    """
    After `helm pull --untar -d dest`, helm creates:
        dest/<chart-short-name>/values.yaml
        dest/<chart-short-name>/Chart.yaml
        ...

    This function finds that subdirectory (the one that contains values.yaml).
    Returns None if not found yet.
    """
    for candidate in dest.iterdir():
        if candidate.is_dir() and (candidate / "values.yaml").exists():
            return candidate
    return None


async def pull_chart(chart: str, version: str) -> Path:
    """
    Download and untar a chart version.
    Returns the extracted chart directory (the one containing values.yaml).
    Uses a local disk cache keyed by chart+version.
    """
    # Cache key: replace "/" → "_"  e.g. "grafana-community/loki" → "grafana-community_loki"
    cache_key = chart.replace("/", "_")
    dest = HELM_CACHE / cache_key / version
    dest.mkdir(parents=True, exist_ok=True)

    # Check cache — only valid if the subdirectory with values.yaml already exists
    cached = _find_chart_dir(dest)
    if cached is not None:
        return cached

    # Not cached — pull and untar into dest
    code, _, err = await _run(
        "helm", "pull", chart,
        "--version", version,
        "--untar",
        "-d", str(dest),
    )
    if code != 0:
        raise RuntimeError(f"helm pull {chart}@{version} failed:\n{err}")

    # Find the extracted chart subdirectory
    chart_dir = _find_chart_dir(dest)
    if chart_dir is None:
        # Fallback: return any subdirectory (handles edge cases)
        subdirs = [p for p in dest.iterdir() if p.is_dir()]
        if subdirs:
            return subdirs[0]
        raise RuntimeError(
            f"helm pull succeeded but no chart directory found in {dest}. "
            f"Contents: {list(dest.iterdir())}"
        )

    return chart_dir


async def render_template(chart_dir: Path, values_path: Path) -> str:
    """Run `helm template` and return rendered manifest text."""
    code, out, err = await _run(
        "helm", "template", "chartsmith", str(chart_dir),
        "-f", str(values_path),
    )
    if code != 0:
        return f"# RENDER ERROR\n{err}"
    return out
