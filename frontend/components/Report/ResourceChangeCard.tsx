"use client";
import { useState } from "react";
import { Card, Pill } from "../ui";
import { FONT_DISPLAY, FONT_MONO, COLORS, SEV_META } from "@/lib/theme";

interface ResourceChange {
  severity: "critical" | "high" | "medium" | "safe";
  change_type: "added" | "removed" | "modified" | "deprecated_api";
  kind: string;
  name: string;
  namespace: string;
  api_version_old: string | null;
  api_version_new: string | null;
  title: string;
  old_yaml: string;
  new_yaml: string;
  note: string | null;
}

const CHANGE_META: Record<string, { label: string; color: string }> = {
  added:          { label: "Added",          color: COLORS.mint },
  removed:        { label: "Removed",        color: COLORS.rose },
  modified:       { label: "Modified",       color: COLORS.violet },
  deprecated_api: { label: "API Deprecated", color: COLORS.ember },
};

/**
 * Expand a YAML string so embedded \n sequences become real newlines.
 * This handles ConfigMap data fields that store multiline content as
 * escaped strings (e.g. nginx.conf stored as one long \n-separated string).
 */
function expandYaml(raw: string): string {
  if (!raw) return "";
  // Replace escaped \n with real newlines, \t with tabs
  // But only inside quoted YAML string values (after ": ")
  const lines = raw.split("\n");
  const result: string[] = [];

  for (const line of lines) {
    // Detect lines where value contains \n — e.g.:  key: "foo\nbar\nbaz"
    const match = line.match(/^(\s*\S+:\s+["']?)(.*\\n.*)["']?$/);
    if (match && line.includes("\\n")) {
      const indent = line.match(/^(\s*)/)?.[1] ?? "";
      const keyPart = match[1];
      const valuePart = match[2].replace(/\\t/g, "  ").replace(/\\n/g, "\n");
      // Emit the key on its own line, then the value expanded with extra indent
      result.push(`${indent}${keyPart.trim()}`);
      const valueLines = valuePart.split("\n");
      for (const vl of valueLines) {
        result.push(`${indent}  ${vl}`);
      }
    } else {
      result.push(line);
    }
  }
  return result.join("\n");
}

/** LCS-based unified diff between two texts */
function unifiedDiff(
  oldText: string,
  newText: string
): Array<{ type: "add" | "remove" | "context"; text: string }> {
  const oldLines = expandYaml(oldText).split("\n");
  const newLines = expandYaml(newText).split("\n");

  if (!oldText && newText) return newLines.map((t) => ({ type: "add", text: t }));
  if (oldText && !newText) return oldLines.map((t) => ({ type: "remove", text: t }));

  const m = oldLines.length;
  const n = newLines.length;

  // Build LCS DP table
  const dp: Uint16Array[] = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = oldLines[i] === newLines[j]
        ? dp[i + 1][j + 1] + 1
        : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  // Traceback
  const raw: Array<{ type: "add" | "remove" | "context"; text: string }> = [];
  let i = 0, j = 0;
  while (i < m || j < n) {
    if (i < m && j < n && oldLines[i] === newLines[j]) {
      raw.push({ type: "context", text: oldLines[i] }); i++; j++;
    } else if (j < n && (i >= m || dp[i][j + 1] >= dp[i + 1][j])) {
      raw.push({ type: "add", text: newLines[j] }); j++;
    } else {
      raw.push({ type: "remove", text: oldLines[i] }); i++;
    }
  }

  // Collapse unchanged context — keep 3 lines around each change
  const CONTEXT = 3;
  const keep = new Set<number>();
  raw.forEach(({ type }, idx) => {
    if (type !== "context") {
      for (let k = Math.max(0, idx - CONTEXT); k <= Math.min(raw.length - 1, idx + CONTEXT); k++) {
        keep.add(k);
      }
    }
  });

  const collapsed: typeof raw = [];
  let skipped = 0;
  raw.forEach((line, idx) => {
    if (keep.has(idx)) {
      if (skipped > 0) {
        collapsed.push({ type: "context", text: `@@ -${idx - skipped + 1},+${idx + 1} ${skipped} unchanged line(s) @@` });
        skipped = 0;
      }
      collapsed.push(line);
    } else {
      skipped++;
    }
  });
  if (skipped > 0) {
    collapsed.push({ type: "context", text: `@@ ${skipped} unchanged line(s) @@` });
  }

  return collapsed;
}

function UnifiedDiffViewer({ oldYaml, newYaml }: { oldYaml: string; newYaml: string }) {
  const lines = unifiedDiff(oldYaml, newYaml);

  return (
    <pre style={{
      fontFamily: FONT_MONO, fontSize: 12, padding: 0,
      borderRadius: 8, background: "#0D1117",
      border: `1px solid ${COLORS.line}`,
      overflow: "auto", lineHeight: 1.6,
      maxHeight: 520, margin: 0,
    }}>
      {lines.map((line, idx) => {
        const isAdd    = line.type === "add";
        const isRemove = line.type === "remove";
        const isMeta   = line.text.startsWith("@@");
        return (
          <div key={idx} style={{
            display: "flex",
            background: isAdd ? "#1a2d1a" : isRemove ? "#2d1a1a" : isMeta ? "#1a1a2d" : "transparent",
            borderLeft: `3px solid ${isAdd ? COLORS.mint : isRemove ? COLORS.rose : "transparent"}`,
          }}>
            <span style={{
              width: 20, textAlign: "center", flexShrink: 0, userSelect: "none",
              color: isAdd ? COLORS.mint : isRemove ? COLORS.rose : COLORS.mute,
              fontSize: 11, padding: "1px 0",
            }}>
              {isAdd ? "+" : isRemove ? "−" : " "}
            </span>
            <span style={{
              padding: "1px 8px 1px 4px",
              color: isAdd ? COLORS.mint : isRemove ? COLORS.rose : isMeta ? COLORS.violet : COLORS.mute,
              whiteSpace: "pre",
            }}>
              {line.text}
            </span>
          </div>
        );
      })}
    </pre>
  );
}

export function ResourceChangeCard({ change }: { change: ResourceChange }) {
  const [expanded, setExpanded] = useState(false);
  const sev  = SEV_META[change.severity];
  const chg  = CHANGE_META[change.change_type] ?? { label: change.change_type, color: COLORS.mute };
  const hasDiff = !!(change.old_yaml || change.new_yaml);

  return (
    <Card style={{ padding: 0, overflow: "hidden", marginBottom: 10 }}>
      <div style={{ display: "flex" }}>
        <div style={{ width: 4, flexShrink: 0, background: sev.color }} />
        <div style={{ padding: "14px 18px", flex: 1, minWidth: 0 }}>

          <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
            <Pill color={sev.color}>{sev.label}</Pill>
            <Pill color={chg.color}>{chg.label}</Pill>
            <span style={{ fontFamily: FONT_MONO, fontSize: 11, color: COLORS.mute }}>{change.kind}</span>
            {change.api_version_old && change.api_version_new && change.api_version_old !== change.api_version_new && (
              <span style={{ fontFamily: FONT_MONO, fontSize: 11, color: COLORS.ember }}>
                {change.api_version_old} → {change.api_version_new}
              </span>
            )}
          </div>

          <div style={{ fontFamily: FONT_DISPLAY, fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
            {change.name}
            {change.namespace !== "default" && (
              <span style={{ color: COLORS.mute, fontWeight: 400, fontSize: 13, marginLeft: 8 }}>
                · ns: {change.namespace}
              </span>
            )}
          </div>

          {change.note && (
            <div style={{
              margin: "8px 0", padding: "8px 12px", borderRadius: 6,
              background: COLORS.panelHi, border: `1px solid ${COLORS.line}`,
              fontSize: 12, color: COLORS.mute, lineHeight: 1.6,
            }}>
              <span style={{ color: COLORS.ember, fontWeight: 600 }}>Note · </span>
              {change.note}
            </div>
          )}

          {hasDiff && (
            <button onClick={() => setExpanded((x) => !x)} style={{
              background: "none", border: `1px solid ${COLORS.line}`,
              borderRadius: 6, color: COLORS.violet, cursor: "pointer",
              fontSize: 12, fontWeight: 600, padding: "4px 10px", marginTop: 6,
            }}>
              {expanded ? "▼ Hide diff" : "▶ Show diff"}
            </button>
          )}

          {expanded && hasDiff && (
            <div style={{ marginTop: 10 }}>
              <UnifiedDiffViewer oldYaml={change.old_yaml} newYaml={change.new_yaml} />
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export function ChangesList({ changes, filter }: { changes: ResourceChange[]; filter: string | null }) {
  const filtered = filter ? changes.filter((c) => c.severity === filter) : changes;
  if (filtered.length === 0) {
    return (
      <div style={{
        padding: 32, textAlign: "center", color: COLORS.mute, fontSize: 14,
        background: COLORS.panel, borderRadius: 12, border: `1px solid ${COLORS.line}`,
      }}>
        {filter ? `No ${filter} severity changes.` : "No changes detected between these versions."}
      </div>
    );
  }
  return <div>{filtered.map((c, i) => <ResourceChangeCard key={i} change={c} />)}</div>;
}
