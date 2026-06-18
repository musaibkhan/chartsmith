"""DeepDiff-based comparison of chart values schemas + user overrides."""
from __future__ import annotations
from typing import Any
from deepdiff import DeepDiff


def _flatten(d: dict, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dict to {'a.b.c': value}."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def _normalize_path(path: str) -> str:
    """Convert DeepDiff path root['a']['b'] → a.b"""
    return (
        path.replace("root", "")
            .replace("['", ".")
            .replace("']", "")
            .lstrip(".")
    )


def schema_diff(old_values: dict, new_values: dict) -> dict:
    """Return a structured summary: removed keys, added keys, type changes, default changes."""
    diff = DeepDiff(old_values, new_values, ignore_order=True, view="tree")

    removed = [_normalize_path(str(c.path())) for c in diff.get("dictionary_item_removed", [])]
    added   = [_normalize_path(str(c.path())) for c in diff.get("dictionary_item_added", [])]
    type_changes = [
        {
            "path":     _normalize_path(str(c.path())),
            "old_type": type(c.t1).__name__,
            "new_type": type(c.t2).__name__,
            "old":      str(c.t1)[:120],
            "new":      str(c.t2)[:120],
        }
        for c in diff.get("type_changes", [])
    ]
    default_changes = [
        {
            "path": _normalize_path(str(c.path())),
            "old":  str(c.t1)[:120],
            "new":  str(c.t2)[:120],
        }
        for c in diff.get("values_changed", [])
    ]

    return {
        "removed_keys":   removed,
        "added_keys":     added,
        "type_changes":   type_changes,
        "default_changes": default_changes,
    }


def affected_user_keys(user_values: dict, sdiff: dict) -> list[dict]:
    """
    For every key the user overrides, check if the schema changed it.
    Returns a list of dicts with: key, user_value, change_type, detail.
    This is what gets sent directly to GPT — NOT the raw schema diff.
    """
    flat_user = _flatten(user_values)
    removed_set = set(sdiff["removed_keys"])
    type_map    = {e["path"]: e for e in sdiff["type_changes"]}
    default_map = {e["path"]: e for e in sdiff["default_changes"]}

    affected = []
    for user_key, user_val in flat_user.items():
        # 1. Exact key removed
        if user_key in removed_set:
            affected.append({
                "key":         user_key,
                "user_value":  str(user_val)[:200],
                "change_type": "removed",
                "detail":      "This key no longer exists in the new chart version.",
            })
            continue

        # 2. Parent key removed (e.g. user sets a.b.c but 'a.b' was removed)
        parent_removed = any(
            user_key.startswith(r + ".") for r in removed_set
        )
        if parent_removed:
            parent = next(r for r in removed_set if user_key.startswith(r + "."))
            affected.append({
                "key":         user_key,
                "user_value":  str(user_val)[:200],
                "change_type": "parent_removed",
                "detail":      f"Parent key '{parent}' was removed from the chart.",
            })
            continue

        # 3. Type changed
        if user_key in type_map:
            e = type_map[user_key]
            affected.append({
                "key":         user_key,
                "user_value":  str(user_val)[:200],
                "change_type": "type_changed",
                "detail":      f"Type changed from {e['old_type']} to {e['new_type']}. "
                               f"Old default: {e['old']}, new default: {e['new']}",
            })
            continue

        # 4. Default value changed (user may need to review)
        if user_key in default_map:
            e = default_map[user_key]
            affected.append({
                "key":         user_key,
                "user_value":  str(user_val)[:200],
                "change_type": "default_changed",
                "detail":      f"Default changed from '{e['old']}' to '{e['new']}'. "
                               f"Your explicit value is preserved but review intent.",
            })

    return affected


def user_keys_summary(user_values: dict, sdiff: dict) -> dict:
    """
    High-level summary for the GPT prompt:
      - total user overrides
      - which are affected and how
      - which are safe (not touched by the diff)
    """
    flat_user  = _flatten(user_values)
    affected   = affected_user_keys(user_values, sdiff)
    affected_keys = {a["key"] for a in affected}
    safe_keys  = [k for k in flat_user if k not in affected_keys]

    return {
        "total_user_overrides": len(flat_user),
        "affected_count":       len(affected),
        "safe_count":           len(safe_keys),
        "affected_keys":        affected,   # full detail — send this to GPT
        "safe_keys":            safe_keys,  # just names — for stats
    }
