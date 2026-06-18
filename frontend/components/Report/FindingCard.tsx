"use client";
import { Card, Pill } from "../ui";
import { FONT_DISPLAY, FONT_MONO, COLORS, SEV_META } from "@/lib/theme";

export function FindingCard({ f }: { f: any }) {
  const m = SEV_META[f.severity];
  return (
    <Card style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ display: "flex" }}>
        <div style={{ width: 4, background: m.color }} />
        <div style={{ padding: 20, flex: 1 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
            <Pill color={m.color}>{m.label}</Pill>
            {f.since && <span style={{ fontFamily: FONT_MONO, fontSize: 12, color: COLORS.mute }}>since {f.since}</span>}
          </div>
          <div style={{ fontFamily: FONT_DISPLAY, fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{f.title}</div>
          <code style={{ fontFamily: FONT_MONO, fontSize: 12, color: COLORS.violet }}>{f.key}</code>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 14 }}>
            <Snippet label="Yours" color={COLORS.rose} body={f.yours} />
            <Snippet label="Migrate to" color={COLORS.mint} body={f.fix} />
          </div>

          {f.note && (
            <div style={{
              marginTop: 12, padding: "10px 12px", borderRadius: 8,
              background: COLORS.panelHi, border: `1px solid ${COLORS.line}`,
              fontSize: 12, color: COLORS.mute, lineHeight: 1.6,
            }}>
              <span style={{ color: COLORS.ember, fontWeight: 600 }}>Note · </span>{f.note}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function Snippet({ label, color, body }: any) {
  return (
    <div>
      <div style={{ fontSize: 11, color: COLORS.mute, marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.6 }}>{label}</div>
      <pre style={{
        background: COLORS.bg, border: `1px solid ${color}33`, padding: 12, borderRadius: 8,
        fontFamily: FONT_MONO, fontSize: 12, color, margin: 0, overflow: "auto", lineHeight: 1.5,
      }}>{body}</pre>
    </div>
  );
}
