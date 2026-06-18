"use client";
import { Card, Pill, Button } from "../ui";
import { FONT_DISPLAY, FONT_MONO, COLORS, SEV_META } from "@/lib/theme";

export function SummaryCard({ report, filter, setFilter, onBack }: any) {
  return (
    <Card style={{ padding: 28 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
            <Pill color={COLORS.violet}>analysis complete</Pill>
            <span style={{ fontSize: 12, color: COLORS.mute, fontFamily: FONT_MONO }}>
              wrapper: {report.wrapper_key || "—"} · context: {report.context}
            </span>
          </div>
          <div style={{ fontFamily: FONT_DISPLAY, fontSize: 26, fontWeight: 600, letterSpacing: -0.4 }}>
            {report.chart} <span style={{ color: COLORS.mute }}>·</span> {report.from_version}
            <span style={{ color: COLORS.ember }}> → </span>{report.to_version}
          </div>
          {/* ── Use changes (not findings) ── */}
          <div style={{ color: COLORS.mute, fontSize: 13, marginTop: 4 }}>
            {report.stats.total_changes ?? report.changes?.length ?? 0} changes detected
            {report.summary && (
              <span style={{ marginLeft: 8, color: COLORS.mute }}>· {report.summary.split("\n")[0]}</span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button onClick={onBack}>← Re-run</Button>
          <Button primary onClick={() => exportMarkdown(report)}>Export Markdown</Button>
        </div>
      </div>

      {/* Severity filter tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 24 }}>
        {(["critical", "high", "medium", "safe"] as const).map((k) => {
          const m = SEV_META[k];
          const n = (report.stats as any)[k] ?? 0;
          const active = filter === k;
          return (
            <button key={k} onClick={() => setFilter(active ? null : k)} style={{
              background: active ? m.color + "1A" : COLORS.panelHi,
              border: `1px solid ${active ? m.color : COLORS.line}`,
              padding: 16, borderRadius: 10, textAlign: "left", cursor: "pointer", color: COLORS.text,
            }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: m.color, letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 6 }}>
                {m.label}
              </div>
              <div style={{ fontFamily: FONT_DISPLAY, fontSize: 32, fontWeight: 600, lineHeight: 1 }}>{n}</div>
            </button>
          );
        })}
      </div>

      {/* Summary text */}
      {report.summary && (
        <div style={{
          marginTop: 20, padding: "12px 16px", borderRadius: 8,
          background: COLORS.panelHi, border: `1px solid ${COLORS.line}`,
          fontSize: 13, color: COLORS.mute, lineHeight: 1.6,
          whiteSpace: "pre-line",
        }}>
          {report.summary}
        </div>
      )}
    </Card>
  );
}

function exportMarkdown(report: any) {
  const lines: string[] = [
    `# ChartSmith Report: ${report.chart}`,
    `**Upgrade:** ${report.from_version} → ${report.to_version}`,
    `**Context:** ${report.context} · Wrapper: ${report.wrapper_key || "—"}`,
    "",
    `## Summary`,
    report.summary || "No summary available.",
    "",
    `## Stats`,
    `| Severity | Count |`,
    `|----------|-------|`,
    `| Critical | ${report.stats.critical} |`,
    `| High     | ${report.stats.high} |`,
    `| Medium   | ${report.stats.medium} |`,
    `| Safe     | ${report.stats.safe} |`,
    "",
    `## Changes`,
    "",
    ...(report.changes || []).map((c: any) => [
      `### [${c.severity.toUpperCase()}] ${c.title}`,
      `- **Kind:** ${c.kind}`,
      `- **Name:** ${c.name}`,
      `- **Change:** ${c.change_type}`,
      c.api_version_old ? `- **API:** ${c.api_version_old} → ${c.api_version_new}` : "",
      c.note ? `- **Note:** ${c.note}` : "",
      "",
      c.old_yaml ? "**Before:**\n```yaml\n" + c.old_yaml + "\n```" : "",
      c.new_yaml ? "**After:**\n```yaml\n" + c.new_yaml + "\n```" : "",
      "",
    ].filter(Boolean).join("\n")),
  ];

  const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `chartsmith-${report.chart.replace("/", "-")}-${report.from_version}-to-${report.to_version}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
