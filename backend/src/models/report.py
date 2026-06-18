"""Pydantic models for analysis requests and reports - v2 with manifest diffs."""
from typing import Literal
from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "safe"]
Context = Literal["plain", "argocd", "umbrella", "helmfile"]
ChangeType = Literal["added", "removed", "modified", "deprecated_api"]


class RepoIn(BaseModel):
    name: str
    url: str


class ChartInfo(BaseModel):
    name: str
    description: str = ""
    latest_version: str = ""


class AnalyzeRequest(BaseModel):
    chart: str
    from_version: str
    to_version: str
    values_yaml: str
    context: Context = "plain"
    wrapper_key: str | None = None


class ResourceChange(BaseModel):
    """A single resource change detected in manifest diff."""
    severity: Severity
    change_type: ChangeType
    kind: str                    # e.g., "Deployment", "Service", "ConfigMap"
    name: str                    # Resource name
    namespace: str = "default"   # Namespace
    api_version_old: str | None = None  # e.g., "apps/v1beta1" → deprecated
    api_version_new: str | None = None  # e.g., "apps/v1"
    title: str                   # Human-readable title
    old_yaml: str = ""          # Full old resource YAML
    new_yaml: str = ""          # Full new resource YAML
    note: str | None = None     # Extra context


class ReportStats(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    safe: int = 0
    total_changes: int = 0


class UpgradePath(BaseModel):
    description: str
    intermediate_version: str


class AnalyzeReport(BaseModel):
    chart: str
    from_version: str
    to_version: str
    wrapper_key: str | None
    context: Context
    stats: ReportStats
    changes: list[ResourceChange] = Field(default_factory=list)
    upgrade_path: list[UpgradePath] = Field(default_factory=list)
    summary: str = ""
