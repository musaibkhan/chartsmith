"""GPT-4o synthesizer — sends only pre-filtered, user-relevant context."""
from __future__ import annotations
import json, os, re
from typing import Any
from openai import AsyncOpenAI

from .prompts import SYSTEM
from src.models.report import AnalyzeReport, AnalyzeRequest, ReportStats, Finding

_client: AsyncOpenAI | None = None


def _client_lazy() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def _repair_json(text: str) -> str:
    text = re.sub(r'^```(?:json)?\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    text = text.strip()
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    open_braces  = text.count('{')
    close_braces = text.count('}')
    if open_braces > close_braces:
        text += '}' * (open_braces - close_braces)
    return text


def _compute_stats(findings: list[dict]) -> ReportStats:
    stats = ReportStats(critical=0, high=0, medium=0, safe=0, total_keys=0)
    for f in findings:
        sev = f.get("severity", "safe")
        if   sev == "critical": stats.critical += 1
        elif sev == "high":     stats.high     += 1
        elif sev == "medium":   stats.medium   += 1
        elif sev == "safe":     stats.safe     += 1
    stats.total_keys = len(findings)
    return stats


def _normalize_findings(raw: Any) -> list[Finding]:
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            out.append(Finding(
                severity=item.get("severity", "safe"),
                key=item.get("key", ""),
                title=item.get("title", ""),
                yours=item.get("yours", ""),
                fix=item.get("fix", ""),
                note=item.get("note") or None,
                since=item.get("since") or None,
            ))
        except Exception as e:
            print(f"[WARN] Skipped malformed finding: {e}")
    return out


def _normalize_upgrade_path(raw: Any) -> list[str]:
    """Accept either list[str] or list[{intermediate_version, description}]."""
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            v = item.get("intermediate_version") or item.get("version") or ""
            if v:
                out.append(v)
    return out


def _build_payload(
    req: AnalyzeRequest,
    user_keys_summary: dict,
    breaking_bullets: list[str],
) -> dict:
    """
    Build a LEAN prompt payload.

    Key insight: instead of sending 30k tokens of raw DeepDiff output,
    we send only the pre-computed intersection of:
      - keys the USER overrides
      - keys the CHART changed between versions

    GPT's job is then to:
      1. Classify each affected key by severity
      2. Produce the 'yours' snippet + 'fix' snippet
      3. Suggest an upgrade path
    """
    return {
        "chart":        req.chart,
        "from_version": req.from_version,
        "to_version":   req.to_version,
        "wrapper_key":  req.wrapper_key,
        "context":      req.context,

        # ── Pre-filtered: only keys the user sets AND the chart changed ──
        # This is the critical fix — not the raw full schema diff.
        "affected_user_keys": user_keys_summary["affected_keys"],   # list[{key, user_value, change_type, detail}]
        "safe_user_keys":     user_keys_summary["safe_keys"],       # list[str] — for context
        "total_user_overrides": user_keys_summary["total_user_overrides"],

        # ── Release notes (capped) ──
        "breaking_changes_from_releases": breaking_bullets[:40],
    }


async def _call_gpt(payload: dict, model: str) -> dict:
    """Call GPT with JSON mode + repair fallback. Returns parsed dict."""
    client = _client_lazy()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": json.dumps(payload)},
    ]

    # Try structured outputs first (gpt-4o only)
    try:
        resp = await client.chat.completions.create(
            model=model,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "AnalyzeReport",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "required": ["findings", "upgrade_path", "summary"],
                        "additionalProperties": False,
                        "properties": {
                            "findings": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["severity", "key", "title", "yours", "fix", "note", "since"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "safe"]},
                                        "key":      {"type": "string"},
                                        "title":    {"type": "string"},
                                        "yours":    {"type": "string"},
                                        "fix":      {"type": "string"},
                                        "note":     {"type": ["string", "null"]},
                                        "since":    {"type": ["string", "null"]},
                                    },
                                },
                            },
                            "upgrade_path": {"type": "array", "items": {"type": "string"}},
                            "summary":      {"type": "string"},
                        },
                    },
                },
            },
            temperature=0.1,
            messages=messages,
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        print(f"[DEBUG] Structured outputs failed ({type(e).__name__}), falling back to JSON mode")

    # Fallback: plain JSON mode
    resp = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=0.1,
        messages=messages,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_repair_json(raw))


async def synthesize(
    req: AnalyzeRequest,
    user_values_unwrapped: dict,
    user_keys_summary: dict,       # ← new param: pre-computed from schema_diff.user_keys_summary()
    breaking_bullets: list[str],
) -> AnalyzeReport:
    """
    Build a lean, pre-filtered payload and call GPT once.
    Falls back to JSON mode + repair if structured outputs fail.
    """
    model   = os.getenv("OPENAI_MODEL", "gpt-4o")
    payload = _build_payload(req, user_keys_summary, breaking_bullets)

    gpt_data = await _call_gpt(payload, model)

    findings     = _normalize_findings(gpt_data.get("findings", []))
    upgrade_path = _normalize_upgrade_path(gpt_data.get("upgrade_path", []))

    return AnalyzeReport.model_validate({
        "chart":        req.chart,
        "from_version": req.from_version,
        "to_version":   req.to_version,
        "wrapper_key":  req.wrapper_key,
        "context":      req.context,
        "stats":        _compute_stats([f.model_dump() for f in findings]),
        "findings":     findings,
        "upgrade_path": upgrade_path,
        "summary":      gpt_data.get("summary", ""),
    })
