"use client";
import { Card, Button } from "../ui";
import { FONT_DISPLAY, FONT_MONO, COLORS } from "@/lib/theme";

export function ChartStep({ charts, chart, setChart, onBack, onNext }: any) {
  return (
    <Card>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
        Pick a chart
      </div>
      <div style={{ color: COLORS.mute, fontSize: 13, marginBottom: 20 }}>
        {charts.length} charts indexed.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
        {charts.map((c: any) => {
          const active = chart === c.name;
          return (
            <button key={c.name} onClick={() => setChart(c.name)} style={{
              textAlign: "left", padding: 14, borderRadius: 10,
              background: active ? COLORS.emberSoft : COLORS.panelHi,
              border: `1px solid ${active ? COLORS.ember : COLORS.line}`,
              cursor: "pointer", color: COLORS.text,
            }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{c.name}</div>
              <div style={{ fontSize: 12, color: COLORS.mute }}>{c.description}</div>
            </button>
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
        <Button onClick={onBack}>← Back</Button>
        <Button primary onClick={onNext} disabled={!chart}>Choose versions →</Button>
      </div>
    </Card>
  );
}
