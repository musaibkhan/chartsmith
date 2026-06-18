"use client";
import { FONT_MONO, COLORS } from "@/lib/theme";

export function UpgradePath({ path }: { path: string[] }) {
  if (!path?.length) return null;
  return (
    <div>
      <div style={{ fontSize: 12, color: COLORS.mute, marginBottom: 10, textTransform: "uppercase", letterSpacing: 0.6 }}>
        Recommended path
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {path.map((v, i) => (
          <div key={v} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              padding: "6px 12px", borderRadius: 999,
              background: i === path.length - 1 ? COLORS.emberSoft : COLORS.panelHi,
              border: `1px solid ${i === path.length - 1 ? COLORS.ember : COLORS.line}`,
              fontFamily: FONT_MONO, fontSize: 12,
            }}>v{v}</div>
            {i < path.length - 1 && <span style={{ color: COLORS.mute }}>→</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
