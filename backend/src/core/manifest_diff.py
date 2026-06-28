"""manifest_diff.py - Stores raw helm template text per resource, no re-serialization."""
from __future__ import annotations
import re
import yaml
from deepdiff import DeepDiff

STATEFUL_KINDS = {"StatefulSet", "PersistentVolumeClaim", "PersistentVolume", "StorageClass"}
DEPRECATED_APIS = {
    "extensions/v1beta1": "apps/v1",
    "apps/v1beta1": "apps/v1",
    "apps/v1beta2": "apps/v1",
    "networking.k8s.io/v1beta1": "networking.k8s.io/v1",
    "policy/v1beta1": "policy/v1",
    "rbac.authorization.k8s.io/v1beta1": "rbac.authorization.k8s.io/v1",
}


class ResourceKey:
    def __init__(self, kind: str, name: str, namespace: str = "default"):
        self.kind = kind
        self.name = name
        self.namespace = namespace

    def __eq__(self, other):
        return isinstance(other, ResourceKey) and (
            self.kind == other.kind and
            self.name == other.name and
            self.namespace == other.namespace
        )

    def __hash__(self):
        return hash((self.kind, self.name, self.namespace))


def parse_manifests(raw_yaml: str) -> dict[ResourceKey, tuple[dict, str]]:
    """
    Parse helm template output.
    Returns: {ResourceKey: (parsed_dict, raw_text)}
    
    KEY: we keep the RAW TEXT of each segment so we never re-serialize.
    This preserves real newlines in ConfigMap data, nginx.conf, etc.
    """
    objects: dict[ResourceKey, tuple[dict, str]] = {}

    # Split on --- document separators
    segments = re.split(r'\n---\n|^---\n', raw_yaml, flags=re.MULTILINE)

    for seg in segments:
        if not seg.strip():
            continue

        # Strip helm comment/warning lines but keep the raw YAML content intact
        lines = []
        for line in seg.splitlines():
            stripped = line.strip()
            if re.match(r'^#|^WARNING|^W\d|^coalesce\.go|^chart\.go|^Schema\(', stripped):
                continue
            lines.append(line)

        clean = "\n".join(lines).strip()
        if not clean:
            continue

        try:
            doc = yaml.safe_load(clean)
        except yaml.YAMLError:
            continue

        if not isinstance(doc, dict) or not doc.get("kind"):
            continue

        kind = doc.get("kind", "Unknown")
        metadata = doc.get("metadata", {}) or {}
        name = metadata.get("name", "?")
        namespace = metadata.get("namespace", "default")

        key = ResourceKey(kind, name, namespace)
        # Store both parsed dict (for diffing) AND raw text (for display)
        objects[key] = (doc, clean)

    print(f"[DEBUG] Parsed {len(objects)} resources")
    return objects


# ── K8s-aware severity rules ────────────────────────────────────────────────
# Immutable fields whose change risks data loss / forces recreation.
_DATA_RISK_FIELDS = {
    "StatefulSet": ["volumeClaimTemplates", "serviceName", "podManagementPolicy"],
}
# Immutable fields whose change requires delete+recreate (no data risk).
_IMMUTABLE_FIELDS = {
    "StatefulSet": ["selector"],
    "Deployment":  ["selector"],
    "DaemonSet":   ["selector"],
    "Service":     ["clusterIP"],
}
# Path fragments considered cosmetic — changes confined to these don't break anything.
_COSMETIC_MARKERS = (
    "['labels']", "['annotations']", "['securityContext']", "['seccompProfile']",
    "helm.sh/chart", "app.kubernetes.io/version", "app.kubernetes.io/managed-by",
)
_WORKLOADS = ("StatefulSet", "Deployment", "DaemonSet")
_STORAGE_KINDS = ("StatefulSet", "PersistentVolumeClaim", "PersistentVolume")


def _changed_paths(diff) -> list[str]:
    """All DeepDiff paths touched, as 'root[...]' strings."""
    paths: list[str] = []
    for cat in ("values_changed", "type_changes"):
        if cat in diff:
            paths.extend(str(p) for p in diff[cat].keys())
    for cat in ("dictionary_item_added", "dictionary_item_removed",
                "iterable_item_added", "iterable_item_removed"):
        if cat in diff:
            paths.extend(str(p) for p in diff[cat])
    return paths


def _has(paths: list[str], needle: str) -> bool:
    return any(needle in p for p in paths)


def _real_clusterip_change(old_doc, new_doc) -> bool:
    """clusterIP in `helm template` output flips between None/absent for headless
    services — that's a rendering artifact, not a real immutable change. Only treat
    it as real when both sides are concrete, distinct values."""
    norm = lambda v: None if v in (None, "", "None") else v
    o = norm(((old_doc or {}).get("spec") or {}).get("clusterIP"))
    n = norm(((new_doc or {}).get("spec") or {}).get("clusterIP"))
    return o is not None and n is not None and o != n


def _crd_versions(doc) -> list[str]:
    spec = (doc or {}).get("spec") or {}
    return [v.get("name") for v in (spec.get("versions") or []) if isinstance(v, dict) and v.get("name")]


def _assess_crd(change_type, old_doc, new_doc):
    """CRDs have special upgrade semantics: Helm installs them once and never upgrades
    them in place, and removing one cascade-deletes every custom resource of that type."""
    if change_type == "added":
        return "high", ("New CRD — Helm/ArgoCD may not install it automatically before the "
                        "controller starts. Confirm it is applied (ArgoCD CRD sync hook or "
                        "`kubectl apply -f <crd>`).")
    if change_type == "removed":
        return "critical", ("CRD removed — deleting a CRD cascade-deletes every custom resource of "
                           "that type. Confirm this is intentional and back up affected CRs first.")
    # modified
    old_v, new_v = set(_crd_versions(old_doc)), set(_crd_versions(new_doc))
    added, removed = new_v - old_v, old_v - new_v
    extra = ""
    if added:
        extra += f" New API version(s): {', '.join(sorted(added))}."
    if removed:
        extra += f" Removed API version(s): {', '.join(sorted(removed))}."
    return "critical", ("CRD schema/version changed — Helm does NOT upgrade CRDs in place, so the new "
                       "schema will not apply on `helm upgrade`/ArgoCD sync." + extra +
                       " Apply it manually before rollout: `kubectl apply -f <crd>` "
                       "(or enable an ArgoCD CRD sync hook).")


def _assess(change_type, kind, old_doc, new_doc, diff=None, kind_replacement=False):
    """Return (severity, action) — action is a one-line remediation hint or None."""
    name = (new_doc or old_doc or {}).get("metadata", {}).get("name", "<name>")

    if kind == "CustomResourceDefinition":
        return _assess_crd(change_type, old_doc, new_doc)

    if change_type == "deprecated_api":
        oa = (old_doc or {}).get("apiVersion", "")
        na = (new_doc or {}).get("apiVersion", "")
        return "critical", (f"apiVersion {oa} → {na}: the old API is removed in current Kubernetes "
                            f"versions — the resource will fail to apply until migrated.")

    if change_type == "removed":
        if kind in _STORAGE_KINDS:
            return "critical", (f"{kind} removed — deleting it can destroy persistent data. "
                               f"Confirm this is a rename, or back up/migrate volumes first.")
        if kind in ("Deployment", "DaemonSet"):
            if kind_replacement:
                return "high", (f"{kind} removed, but other {kind}s exist in the new version — "
                               f"likely renamed. Verify the replacement covers this workload.")
            return "critical", f"{kind} removed and not replaced — this workload will be deleted (downtime)."
        if kind in ("PodDisruptionBudget", "HorizontalPodAutoscaler"):
            if kind_replacement:
                return "high", (f"{kind} removed, but similar resources exist in the new version — "
                               f"likely restructured (e.g. per-component). Verify the replacements "
                               f"still cover the same workloads.")
            return "critical", (f"{kind} removed with no replacement — availability/scaling protection "
                               f"is lost on upgrade.")
        if kind in ("Service", "Ingress"):
            return "high", f"{kind} removed — its endpoints/DNS will disappear; check dependents."
        if kind in ("ConfigMap", "Secret"):
            if kind_replacement:
                return "medium", None
            return "high", (f"{kind} removed with no replacement — pods that mount it may fail to "
                           f"start. Verify nothing references it.")
        return "medium", None

    if change_type == "added":
        if kind in _STORAGE_KINDS:
            return "medium", f"New {kind} introduced — new storage will be provisioned."
        return "safe", None

    # ── modified ──────────────────────────────────────────────────────────────
    oa = (old_doc or {}).get("apiVersion", "")
    na = (new_doc or {}).get("apiVersion", "")
    if oa and na and oa != na:
        if oa in DEPRECATED_APIS:
            return "critical", (f"apiVersion {oa} → {na}: old API removed in current Kubernetes — "
                               f"resource won't apply until migrated.")
        return "high", f"apiVersion changed {oa} → {na}; confirm the cluster serves the new API."

    paths = _changed_paths(diff or {})

    for f in _DATA_RISK_FIELDS.get(kind, []):
        if _has(paths, f"['{f}']"):
            return "critical", (f"{kind} '{f}' changed — this field is immutable. The resource can't "
                               f"update in place; recreate it (`kubectl delete {kind.lower()} {name} "
                               f"--cascade=orphan`) to apply without data loss.")

    if _has(paths, "['storageClassName']") or (_has(paths, "['storage']") and _has(paths, "['resources']")):
        return "critical", ("PVC storage class/size changed — PVCs are immutable; this may require "
                           "manual PVC recreation and data migration.")

    for f in _IMMUTABLE_FIELDS.get(kind, []):
        if _has(paths, f"['{f}']"):
            if f == "clusterIP" and not _real_clusterip_change(old_doc, new_doc):
                continue  # None/absent headless rendering artifact, not a real change
            return "critical", (f"{kind} '{f}' is immutable — applying this requires deleting and "
                               f"recreating the resource.")

    # Cosmetic-only change (labels/annotations/securityContext/chart-version)?
    non_cosmetic = [p for p in paths if not any(c in p for c in _COSMETIC_MARKERS)]
    if paths and not non_cosmetic:
        return "safe", None

    if kind == "Service":
        if _has(paths, "['type']"):
            return "high", "Service type changed — how the service is exposed changes; verify clients."
        if _has(paths, "['ports']"):
            return "medium", "Service ports changed — verify dependents use the new ports."
        return "medium", None

    if kind in _WORKLOADS:
        if _has(paths, "['replicas']"):
            return "high", "Replica count changed — running capacity will change on upgrade."
        return "medium", None  # rolling update (image/env/SA/resources) — expected churn, no data risk

    return "medium", None


def _explain_diff(diff: dict) -> str:
    parts = []
    if "values_changed" in diff:
        parts.append(f"{len(diff['values_changed'])} value(s) changed")
    if "dictionary_item_removed" in diff:
        parts.append(f"{len(diff['dictionary_item_removed'])} field(s) removed")
    if "dictionary_item_added" in diff:
        parts.append(f"{len(diff['dictionary_item_added'])} field(s) added")
    if "type_changes" in diff:
        parts.append(f"{len(diff['type_changes'])} type(s) changed")
    return "; ".join(parts) if parts else "configuration modified"


def compare_manifests(old_yaml: str, new_yaml: str) -> list[dict]:
    old_objects = parse_manifests(old_yaml)
    new_objects = parse_manifests(new_yaml)

    print(f"[INFO] Old: {len(old_objects)} resources, New: {len(new_objects)} resources")

    changes = []
    matched_old: set[ResourceKey] = set()
    matched_new: set[ResourceKey] = set()

    # Pass 1: exact matches → check modifications
    for key in old_objects:
        if key not in new_objects:
            continue
        matched_old.add(key)
        matched_new.add(key)

        old_doc, old_raw = old_objects[key]
        new_doc, new_raw = new_objects[key]

        old_api = old_doc.get("apiVersion", "")
        new_api = new_doc.get("apiVersion", "")
        is_deprecated = old_api != new_api and old_api in DEPRECATED_APIS

        diff = DeepDiff(old_doc, new_doc, ignore_order=True)
        if not diff:
            continue

        change_type = "deprecated_api" if is_deprecated else "modified"
        severity, action = _assess(change_type, key.kind, old_doc, new_doc, diff)
        changes.append({
            "change_type": change_type,
            "severity": severity,
            "kind": key.kind,
            "name": key.name,
            "namespace": key.namespace,
            "api_version_old": old_api or None,
            "api_version_new": new_api or None,
            "old_yaml": old_raw,   # ← raw text, no re-serialization
            "new_yaml": new_raw,   # ← raw text, no re-serialization
            "title": f"{key.kind}/{key.name}: " + (
                f"API changed {old_api} → {new_api}" if is_deprecated else _explain_diff(diff)
            ),
            "note": _explain_diff(diff),
            "action": action,
        })

    # Group by kind for context notes
    old_by_kind: dict[str, list] = {}
    new_by_kind: dict[str, list] = {}
    for k in old_objects:
        old_by_kind.setdefault(k.kind, []).append(k)
    for k in new_objects:
        new_by_kind.setdefault(k.kind, []).append(k)

    # Pass 2: unmatched old → removed
    for key, (old_doc, old_raw) in old_objects.items():
        if key in matched_old:
            continue
        new_same = new_by_kind.get(key.kind, [])
        note = (
            f"Renamed/restructured. New {key.kind} resources: "
            + ", ".join(k.name for k in new_same[:5])
            if new_same else
            f"{key.kind} no longer present in new chart version."
        )
        severity, action = _assess("removed", key.kind, old_doc, None,
                                   kind_replacement=bool(new_same))
        changes.append({
            "change_type": "removed",
            "severity": severity,
            "kind": key.kind,
            "name": key.name,
            "namespace": key.namespace,
            "api_version_old": old_doc.get("apiVersion"),
            "api_version_new": None,
            "old_yaml": old_raw,   # ← raw text
            "new_yaml": "",
            "title": f"{key.kind}/{key.name} removed",
            "note": note,
            "action": action,
        })

    # Pass 3: unmatched new → added
    for key, (new_doc, new_raw) in new_objects.items():
        if key in matched_new:
            continue
        old_same = old_by_kind.get(key.kind, [])
        note = (
            "Possibly renamed from: " + ", ".join(k.name for k in old_same[:3])
            if old_same else
            f"Brand new {key.kind} introduced in this chart version."
        )
        severity, action = _assess("added", key.kind, None, new_doc)
        changes.append({
            "change_type": "added",
            "severity": severity,
            "kind": key.kind,
            "name": key.name,
            "namespace": key.namespace,
            "api_version_old": None,
            "api_version_new": new_doc.get("apiVersion"),
            "old_yaml": "",
            "new_yaml": new_raw,   # ← raw text
            "title": f"{key.kind}/{key.name} added",
            "note": note,
            "action": action,
        })

    order = {"critical": 0, "high": 1, "medium": 2, "safe": 3}
    changes.sort(key=lambda c: order.get(c["severity"], 4))

    print(f"[INFO] Changes: {len(changes)} "
          f"(critical={sum(1 for c in changes if c['severity']=='critical')}, "
          f"high={sum(1 for c in changes if c['severity']=='high')}, "
          f"medium={sum(1 for c in changes if c['severity']=='medium')}, "
          f"safe={sum(1 for c in changes if c['severity']=='safe')})")

    return changes


def compute_stats(changes: list[dict]) -> dict:
    stats = {"critical": 0, "high": 0, "medium": 0, "safe": 0, "total_changes": len(changes)}
    for c in changes:
        if c["severity"] in stats:
            stats[c["severity"]] += 1
    return stats
