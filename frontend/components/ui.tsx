"use client";
import { COLORS, FONT_BODY, FONT_MONO } from "@/lib/theme";

export const inputStyle: React.CSSProperties = {
  width: "100%", background: COLORS.bg, border: `1px solid ${COLORS.line}`,
  color: COLORS.text, padding: "10px 12px", borderRadius: 8,
  fontFamily: FONT_MONO, fontSize: 13, outline: "none",
};

export function Field({ label, hint, children }: any) {
  return (
    <label style={{ display: "block", marginBottom: 14 }}>
      <div style={{ fontFamily: FONT_BODY, fontSize: 12, color: COLORS.mute, marginBottom: 6,
        textTransform: "uppercase", letterSpacing: 0.6 }}>
        {label}
      </div>
      {children}
      {hint && <div style={{ fontSize: 12, color: COLORS.mute, marginTop: 6 }}>{hint}</div>}
    </label>
  );
}

export function Button({ children, primary, onClick, disabled }: any) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      background: primary ? COLORS.ember : "transparent",
      color: primary ? "#000" : COLORS.text,
      border: primary ? "none" : `1px solid ${COLORS.line}`,
      padding: "10px 18px", borderRadius: 8, fontSize: 13, fontWeight: 600,
      cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.4 : 1,
    }}>{children}</button>
  );
}

export function Card({ children, style }: any) {
  return (
    <div style={{
      background: COLORS.panel, border: `1px solid ${COLORS.line}`,
      borderRadius: 12, padding: 24, ...style,
    }}>{children}</div>
  );
}

export function Pill({ children, color = COLORS.mute }: any) {
  return (
    <span style={{
      fontFamily: FONT_MONO, fontSize: 10, padding: "2px 8px",
      border: `1px solid ${color}55`, color, borderRadius: 999,
      textTransform: "uppercase", letterSpacing: 0.6,
    }}>{children}</span>
  );
}
