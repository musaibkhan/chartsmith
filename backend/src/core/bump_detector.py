"""Detect Helm chart version bumps from a git diff.

Supports three source types:
  - Chart.yaml  (umbrella/parent chart dependencies section)
  - ArgoCD Application manifests (spec.source.targetRevision)
  - helmfile.yaml (releases[].version)
"""
from __future__ import annotations
import subprocess
import yaml
from pathlib import Path


def _git(*args: str) -> tuple[str, int]:
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True,
    )
    return result.stdout, result.returncode


def _file_at_ref(filepath: str, ref: str) -> str | None:
    """Return file content at a given git ref, or None if not found."""
    out, code = _git("show", f"{ref}:{filepath}")
    return out if code == 0 else None


def _changed_yaml_files(base_ref: str, head_ref: str, search_path: str) -> list[str]:
    out, _ = _git(
        "diff", "--name-only", f"{base_ref}..{head_ref}",
        "--", f"{search_path}/**/*.yaml", f"{search_path}/**/*.yml",
        f"{search_path}/*.yaml", f"{search_path}/*.yml",
    )
    files = [f.strip() for f in out.splitlines() if f.strip()]

    # Also try without path filters (git diff --name-only is path-sensitive)
    if not files:
        out, _ = _git("diff", "--name-only", f"{base_ref}..{head_ref}")
        files = [
            f.strip() for f in out.splitlines()
            if f.strip().endswith((".yaml", ".yml"))
        ]

    return files


def _bumps_from_chart_yaml(old: dict, new: dict, filepath: str) -> list[dict]:
    bumps = []
    old_deps = {
        d["name"]: d
        for d in old.get("dependencies", [])
        if isinstance(d, dict) and "name" in d
    }
    for dep in new.get("dependencies", []):
        if not isinstance(dep, dict) or "name" not in dep:
            continue
        name = dep["name"]
        old_dep = old_deps.get(name)
        if not old_dep:
            continue
        old_v = str(old_dep.get("version", ""))
        new_v = str(dep.get("version", ""))
        if old_v and new_v and old_v != new_v:
            repo_url = dep.get("repository") or old_dep.get("repository") or ""
            # In an umbrella chart, the subchart's values are nested under the
            # dependency's alias (if set) or its name. That's the wrapper key.
            wrapper_key = dep.get("alias") or old_dep.get("alias") or name
            bumps.append({
                "chart": name,
                "from_version": old_v,
                "to_version": new_v,
                "repo_url": repo_url,
                "repo_name": None,
                "wrapper_key": wrapper_key,
                "source_file": filepath,
                "source_type": "Chart.yaml",
            })
    return bumps


def _bumps_from_argocd_application(old: dict, new: dict, filepath: str) -> list[dict]:
    if old.get("kind") != "Application" or new.get("kind") != "Application":
        return []
    old_src = (old.get("spec") or {}).get("source") or {}
    new_src = (new.get("spec") or {}).get("source") or {}
    old_rev = str(old_src.get("targetRevision", ""))
    new_rev = str(new_src.get("targetRevision", ""))
    chart = new_src.get("chart") or old_src.get("chart")
    if not (old_rev and new_rev and old_rev != new_rev and chart):
        return []
    return [{
        "chart": chart,
        "from_version": old_rev,
        "to_version": new_rev,
        "repo_url": new_src.get("repoURL") or old_src.get("repoURL") or "",
        "repo_name": None,
        "source_file": filepath,
        "source_type": "argocd_application",
    }]


def _bumps_from_helmfile(old: dict, new: dict, filepath: str) -> list[dict]:
    bumps = []
    old_releases = {
        r.get("name"): r
        for r in old.get("releases", [])
        if isinstance(r, dict) and r.get("name")
    }
    for rel in new.get("releases", []):
        if not isinstance(rel, dict) or not rel.get("name"):
            continue
        old_rel = old_releases.get(rel["name"])
        if not old_rel:
            continue
        old_v = str(old_rel.get("version", ""))
        new_v = str(rel.get("version", ""))
        if old_v and new_v and old_v != new_v:
            bumps.append({
                "chart": rel.get("chart") or old_rel.get("chart") or rel["name"],
                "from_version": old_v,
                "to_version": new_v,
                "repo_url": None,
                "repo_name": None,
                "source_file": filepath,
                "source_type": "helmfile",
            })
    return bumps


def _extract_bumps(old_text: str, new_text: str, filepath: str) -> list[dict]:
    try:
        old = yaml.safe_load(old_text) or {}
        new = yaml.safe_load(new_text) or {}
    except yaml.YAMLError:
        return []

    if not isinstance(old, dict) or not isinstance(new, dict):
        return []

    filename = Path(filepath).name.lower()
    bumps: list[dict] = []

    if filename in ("chart.yaml", "requirements.yaml"):
        bumps += _bumps_from_chart_yaml(old, new, filepath)
    elif new.get("kind") == "Application":
        bumps += _bumps_from_argocd_application(old, new, filepath)
    elif "releases" in new or filename in ("helmfile.yaml", "helmfile.yml"):
        bumps += _bumps_from_helmfile(old, new, filepath)
    else:
        # Try all patterns for unknown filenames
        bumps += _bumps_from_chart_yaml(old, new, filepath)
        bumps += _bumps_from_argocd_application(old, new, filepath)
        bumps += _bumps_from_helmfile(old, new, filepath)

    return bumps


def detect_bumps_from_git(
    base_ref: str,
    head_ref: str = "HEAD",
    search_path: str = ".",
) -> list[dict]:
    """Return a list of chart version bumps detected between two git refs."""
    changed = _changed_yaml_files(base_ref, head_ref, search_path)
    bumps: list[dict] = []

    for filepath in changed:
        old_text = _file_at_ref(filepath, base_ref)
        new_text = _file_at_ref(filepath, head_ref)
        if old_text is None or new_text is None:
            continue
        bumps.extend(_extract_bumps(old_text, new_text, filepath))

    # Deduplicate by (chart, from_version, to_version)
    seen: set[tuple] = set()
    unique: list[dict] = []
    for b in bumps:
        key = (b["chart"], b["from_version"], b["to_version"])
        if key not in seen:
            seen.add(key)
            unique.append(b)

    return unique
