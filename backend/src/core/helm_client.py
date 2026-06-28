from __future__ import annotations
import asyncio, json, os, re, shutil
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


async def pull_chart(chart: str, version: str, repo_url: str | None = None) -> Path:
    """
    Download and untar a chart version.
    Returns the extracted chart directory (the one containing values.yaml).
    Uses a local disk cache keyed by chart+version (+repo_url when given).

    Resolution modes:
      - repo_url is None        → `helm pull <chart>`           (chart = "repo/name")
      - repo_url is http(s)://  → `helm pull <name> --repo <url>`
      - repo_url is oci://      → `helm pull <url>/<name>`       (OCI registry)
    """
    # Cache key includes repo so two same-named charts from different repos don't collide.
    repo_tag = "_" + re.sub(r"[^a-zA-Z0-9]+", "-", repo_url).strip("-") if repo_url else ""
    cache_key = chart.replace("/", "_") + repo_tag
    dest = HELM_CACHE / cache_key / version
    dest.mkdir(parents=True, exist_ok=True)

    # Check cache — only valid if the subdirectory with values.yaml already exists
    cached = _find_chart_dir(dest)
    if cached is not None:
        return cached

    # Build the pull command based on how the chart is addressed.
    if repo_url and repo_url.startswith("oci://"):
        ref = f"{repo_url.rstrip('/')}/{chart}"
        cmd = ["helm", "pull", ref, "--version", version, "--untar", "-d", str(dest)]
    elif repo_url:
        cmd = ["helm", "pull", chart, "--repo", repo_url,
               "--version", version, "--untar", "-d", str(dest)]
    else:
        cmd = ["helm", "pull", chart, "--version", version, "--untar", "-d", str(dest)]

    code, _, err = await _run(*cmd)
    if code != 0:
        loc = f" (repo {repo_url})" if repo_url else ""
        raise RuntimeError(f"helm pull {chart}@{version}{loc} failed:\n{err}")

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


async def render_chart_dir(chart_dir: Path, release: str = "chartsmith") -> str:
    """Render a local chart directory as-is (umbrella parent + its dependency),
    matching what ArgoCD/Helm actually deploys. Fetches subchart deps first."""
    # ponytail: skips sops-encrypted secrets.yaml; add a -f decrypt step if a chart
    # needs decrypted values to render structure.
    await _run("helm", "dependency", "update", str(chart_dir))  # non-fatal if no deps
    base = ["helm", "template", release, str(chart_dir)]
    code, out, err = await _run(*base)
    if code != 0 and "schema" in err.lower():
        code, out, err = await _run(*base, "--skip-schema-validation")
    if code != 0:
        return f"# RENDER ERROR\n{err}"
    return out


async def render_template(chart_dir: Path, values_path: Path) -> str:
    """Run `helm template` and return rendered manifest text.

    If Helm's JSON-schema validation rejects the values (common across major
    chart upgrades — e.g. an int where the schema now wants a string), retry
    with --skip-schema-validation. For a diff we care about the rendered
    manifests, not schema conformance.
    """
    base = ["helm", "template", "chartsmith", str(chart_dir), "-f", str(values_path)]
    code, out, err = await _run(*base)
    if code != 0 and "schema" in err.lower():
        code, out, err = await _run(*base, "--skip-schema-validation")
    if code != 0:
        return f"# RENDER ERROR\n{err}"
    return out
