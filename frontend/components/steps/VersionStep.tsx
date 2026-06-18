"use client";
import { Card, Field, Button, inputStyle } from "../ui";
import { FONT_DISPLAY, COLORS } from "@/lib/theme";

export function VersionStep({ chart, versions, fromV, setFromV, toV, setToV, onBack, onNext }: any) {
  return (
    <Card>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
        Versions for {chart}
      </div>
      <div style={{ color: COLORS.mute, fontSize: 13, marginBottom: 20 }}>
        {versions.length} releases found.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 16, alignItems: "end" }}>
        <Field label="Current version">
          <select style={inputStyle as any} value={fromV} onChange={(e: any) => setFromV(e.target.value)}>
            {versions.map((v: string) => <option key={v} value={v}>{v}</option>)}
          </select>
        </Field>
        <div style={{ fontSize: 22, color: COLORS.ember, paddingBottom: 16 }}>→</div>
        <Field label="Target version">
          <select style={inputStyle as any} value={toV} onChange={(e: any) => setToV(e.target.value)}>
            {versions.map((v: string) => <option key={v} value={v}>{v}</option>)}
          </select>
        </Field>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
        <Button onClick={onBack}>← Back</Button>
        <Button primary onClick={onNext} disabled={!fromV || !toV || fromV === toV}>
          Provide values →
        </Button>
      </div>
    </Card>
  );
}
