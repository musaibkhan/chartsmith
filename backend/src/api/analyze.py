"""Analyze endpoint - pure helm template diff, no AI, no changelog."""
from __future__ import annotations
import os
import tempfile
import yaml
import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException

from src.models.report import AnalyzeRequest, AnalyzeReport, ReportStats, ResourceChange, UpgradePath
from src.core.helm_client import pull_chart, render_template as helm_template
from src.core.unwrap import detect_wrapper, unwrap_values
from src.core.manifest_diff import compare_manifests, compute_stats

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeReport)
async def analyze(req: AnalyzeRequest):
    # ── 1. Pull both chart versions ────────────────────────────────────────
    try:
        old_dir = await pull_chart(req.chart, req.from_version)
    except RuntimeError as e:
        raise HTTPException(400, f"helm pull ({req.chart}@{req.from_version}) failed: {e}")

    try:
        new_dir = await pull_chart(req.chart, req.to_version)
    except RuntimeError as e:
        raise HTTPException(400, f"helm pull ({req.chart}@{req.to_version}) failed: {e}")

    print(f"[INFO] old_dir: {old_dir}")
    print(f"[INFO] new_dir: {new_dir}")

    # ── 2. Detect wrapper key ──────────────────────────────────────────────
    try:
        user_top = yaml.safe_load(req.values_yaml) or {}
    except yaml.YAMLError as e:
        raise HTTPException(400, f"Invalid YAML in values_yaml: {e}")

    wrapper = req.wrapper_key or detect_wrapper(user_top, old_dir / "values.yaml")

    # ── 3. Write values file ───────────────────────────────────────────────
    # CRITICAL: write to a named file that persists for both helm calls.
    # Never use delete=True or unlink before both calls complete.
    # For plain helm: use original text exactly (preserves deploymentMode etc.)
    # For ArgoCD/umbrella: unwrap first, then dump.
    if wrapper:
        user_uw = unwrap_values(req.values_yaml, wrapper)
        values_text = yaml.safe_dump(user_uw, default_flow_style=False, sort_keys=False)
    else:
        values_text = req.values_yaml

    # Write to a persistent temp file (not deleted on close)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, dir="/tmp", prefix="chartsmith_"
    )
    tmp.write(values_text)
    tmp.flush()
    tmp.close()
    values_file = Path(tmp.name)
    print(f"[INFO] Values file: {values_file} ({os.path.getsize(values_file)} bytes)")

    # ── 4. Render manifests ────────────────────────────────────────────────
    try:
        old_manifests = await helm_template(old_dir, values_file)
        new_manifests = await helm_template(new_dir, values_file)
    except Exception as e:
        values_file.unlink(missing_ok=True)
        raise HTTPException(500, f"helm template failed: {e}\n{traceback.format_exc()}")

    # Check for render errors
    if old_manifests.startswith("# RENDER ERROR"):
        values_file.unlink(missing_ok=True)
        raise HTTPException(500, f"helm template failed for {req.from_version}:\n{old_manifests}")
    if new_manifests.startswith("# RENDER ERROR"):
        values_file.unlink(missing_ok=True)
        raise HTTPException(500, f"helm template failed for {req.to_version}:\n{new_manifests}")

    values_file.unlink(missing_ok=True)

    print(f"[INFO] Old manifest: {len(old_manifests)} chars")
    print(f"[INFO] New manifest: {len(new_manifests)} chars")

    # ── 5. Diff ────────────────────────────────────────────────────────────
    try:
        raw_changes = compare_manifests(old_manifests, new_manifests)
    except Exception as e:
        raise HTTPException(500, f"manifest diff failed: {e}\n{traceback.format_exc()}")

    # ── 6. Build response ──────────────────────────────────────────────────
    changes: list[ResourceChange] = []
    for raw in raw_changes:
        try:
            changes.append(ResourceChange(
                severity=raw["severity"],
                change_type=raw["change_type"],
                kind=raw["kind"],
                name=raw["name"],
                namespace=raw["namespace"],
                api_version_old=raw.get("api_version_old"),
                api_version_new=raw.get("api_version_new"),
                title=raw["title"],
                old_yaml=raw.get("old_yaml", ""),
                new_yaml=raw.get("new_yaml", ""),
                note=raw.get("note"),
                action=raw.get("action"),
            ))
        except Exception as e:
            print(f"[WARN] Skipped change: {e}")

    stats_dict = compute_stats(raw_changes)
    stats = ReportStats(
        critical=stats_dict["critical"],
        high=stats_dict["high"],
        medium=stats_dict["medium"],
        safe=stats_dict["safe"],
        total_changes=stats_dict["total_changes"],
    )

    summary = _build_summary(stats, req.from_version, req.to_version)

    return AnalyzeReport(
        chart=req.chart,
        from_version=req.from_version,
        to_version=req.to_version,
        wrapper_key=wrapper or None,
        context=req.context,
        stats=stats,
        changes=changes,
        upgrade_path=[],
        summary=summary,
    )


def _build_summary(stats: ReportStats, from_ver: str, to_ver: str) -> str:
    total = stats.total_changes
    if total == 0:
        return f"Upgrade from {from_ver} to {to_ver}: No breaking changes detected."
    risk = "HIGH" if stats.critical > 0 else "MEDIUM" if stats.high > 0 else "LOW"
    lines = [
        f"Upgrade from {from_ver} to {to_ver}: {total} change(s) detected.",
        f"\nRisk Level: {risk}",
    ]
    if stats.critical > 0:
        lines.append(f"• {stats.critical} critical change(s) requiring immediate attention")
    if stats.high > 0:
        lines.append(f"• {stats.high} high-priority change(s)")
    if stats.medium > 0:
        lines.append(f"• {stats.medium} medium-priority change(s)")
    if stats.safe > 0:
        lines.append(f"• {stats.safe} safe (additive) change(s)")
    lines.append("\nRecommendation: Test in staging before applying to production.")
    return "\n".join(lines)