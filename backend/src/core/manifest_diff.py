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


def _severity(change_type: str, kind: str, old_doc: dict | None, new_doc: dict | None) -> str:
    if change_type == "deprecated_api":
        return "critical"
    if change_type == "removed":
        if kind in STATEFUL_KINDS:
            return "critical"
        if kind in ("Deployment", "DaemonSet", "Ingress"):
            return "critical"
        if kind == "Service":
            return "high"
        return "medium"
    if change_type == "added":
        if kind in STATEFUL_KINDS:
            return "critical"
        if kind in ("Deployment", "DaemonSet"):
            return "high"
        return "safe"
    if change_type == "modified":
        if old_doc and new_doc:
            old_api = old_doc.get("apiVersion", "")
            new_api = new_doc.get("apiVersion", "")
            if old_api != new_api:
                return "critical" if old_api in DEPRECATED_APIS else "high"
            if kind in STATEFUL_KINDS and old_doc.get("spec") != new_doc.get("spec"):
                return "critical"
            if old_doc.get("spec") != new_doc.get("spec"):
                return "high"
        return "medium"
    return "medium"


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
        changes.append({
            "change_type": change_type,
            "severity": _severity(change_type, key.kind, old_doc, new_doc),
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
        changes.append({
            "change_type": "removed",
            "severity": _severity("removed", key.kind, old_doc, None),
            "kind": key.kind,
            "name": key.name,
            "namespace": key.namespace,
            "api_version_old": old_doc.get("apiVersion"),
            "api_version_new": None,
            "old_yaml": old_raw,   # ← raw text
            "new_yaml": "",
            "title": f"{key.kind}/{key.name} removed",
            "note": note,
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
        changes.append({
            "change_type": "added",
            "severity": _severity("added", key.kind, None, new_doc),
            "kind": key.kind,
            "name": key.name,
            "namespace": key.namespace,
            "api_version_old": None,
            "api_version_new": new_doc.get("apiVersion"),
            "old_yaml": "",
            "new_yaml": new_raw,   # ← raw text
            "title": f"{key.kind}/{key.name} added",
            "note": note,
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
