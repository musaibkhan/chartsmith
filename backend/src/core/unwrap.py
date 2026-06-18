"""Detect and strip wrapper keys (ArgoCD Application, umbrella chart, helmfile)."""
from __future__ import annotations
from pathlib import Path
import yaml


def detect_wrapper(user_values: dict, upstream_values: dict | Path) -> str | None:
    """
    Heuristic: if user's top-level keys don't overlap upstream's top-level keys,
    but values[<single_key>] does, that single_key is the wrapper.

    upstream_values can be a dict OR a Path to a values.yaml file.
    """
    if not isinstance(user_values, dict) or not user_values:
        return None

    # Accept Path or dict for upstream_values
    if isinstance(upstream_values, Path):
        try:
            upstream_values = yaml.safe_load(upstream_values.read_text()) or {}
        except Exception:
            upstream_values = {}

    upstream_keys = set(upstream_values.keys()) if isinstance(upstream_values, dict) else set()
    user_keys = set(user_values.keys())
    overlap = user_keys & upstream_keys

    if overlap:
        # User values are already at chart level — no wrapper
        return None

    # Try every top-level key — pick the one whose children overlap upstream most.
    best_key, best_score = None, 0
    for k, v in user_values.items():
        if not isinstance(v, dict):
            continue
        score = len(set(v.keys()) & upstream_keys)
        if score > best_score:
            best_key, best_score = k, score

    return best_key if best_score > 0 else None


def unwrap_values(yaml_text: str, wrapper_key: str | None) -> dict:
    data = yaml.safe_load(yaml_text) or {}
    if wrapper_key and isinstance(data, dict) and wrapper_key in data:
        inner = data[wrapper_key]
        if isinstance(inner, dict):
            return inner
    return data if isinstance(data, dict) else {}