"use client";
import { COLORS, FONT_BODY, FONT_MONO } from "@/lib/theme";

const STEPS = ["Repo", "Chart", "Versions", "Values", "Report"];

export function Stepper({ step }: { step: number }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {STEPS.map((s, i) => {
        const active = i === step, done = i < step;
        return (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 22, height: 22, borderRadius: 6, display: "grid", placeItems: "center",
              fontFamily: FONT_MONO, fontSize: 11,
              background: active ? COLORS.ember : done ? "#3DDC9722" : COLORS.panelHi,
              color: active ? "#000" : done ? COLORS.mint : COLORS.mute,
              border: `1px solid ${active ? COLORS.ember : done ? COLORS.mint + "55" : COLORS.line}`,
            }}>{done ? "✓" : i + 1}</div>
            <span style={{
              fontFamily: FONT_BODY, fontSize: 12,
              color: active ? COLORS.text : COLORS.mute, fontWeight: active ? 600 : 400,
            }}>{s}</span>
            {i < STEPS.length - 1 && <div style={{ width: 18, height: 1, background: COLORS.line, marginLeft: 4 }} />}
          </div>
        );
      })}
    </div>
  );
}
