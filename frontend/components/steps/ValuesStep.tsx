"use client";
import { Card, Field, Button, inputStyle } from "../ui";
import { FONT_DISPLAY, FONT_MONO, COLORS } from "@/lib/theme";

const CONTEXTS = [
  ["plain", "Plain Helm"],
  ["argocd", "ArgoCD"],
  ["umbrella", "Umbrella"],
  ["helmfile", "Helmfile"],
] as const;

export function ValuesStep({
  context, setContext, wrapper, setWrapper, values, setValues,
  onBack, onAnalyze, analyzing, chart, fromV, toV,
}: any) {
  return (
    <Card>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
        Hand over your values.yaml
      </div>
      <div style={{ color: COLORS.mute, fontSize: 13, marginBottom: 20 }}>
        Tell us if the file wraps the chart inside a parent key.
      </div>

      <Field label="Deployment context">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          {CONTEXTS.map(([k, label]) => {
            const active = context === k;
            return (
              <button key={k} onClick={() => setContext(k)} style={{
                padding: "10px 12px", borderRadius: 8,
                background: active ? COLORS.emberSoft : COLORS.panelHi,
                border: `1px solid ${active ? COLORS.ember : COLORS.line}`,
                color: COLORS.text, cursor: "pointer", fontSize: 13,
              }}>{label}</button>
            );
          })}
        </div>
      </Field>

      {context !== "plain" && (
        <Field label="Wrapper key (optional)" hint="If empty, ChartSmith will auto-detect it.">
          <input style={inputStyle} value={wrapper}
                 onChange={(e: any) => setWrapper(e.target.value)} placeholder="e.g. loki" />
        </Field>
      )}

      <Field label="Paste values.yaml" hint="Stays in your browser until you click Analyze.">
        <textarea style={{ ...inputStyle, minHeight: 240, resize: "vertical" }}
          value={values} onChange={(e: any) => setValues(e.target.value)}
          placeholder={"loki:\n  deploymentMode: Distributed\n  ..."} />
      </Field>

      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <Button onClick={onBack}>← Back</Button>
        <Button primary onClick={onAnalyze} disabled={analyzing || !values}>
          {analyzing ? "Analyzing…" : "Analyze upgrade →"}
        </Button>
      </div>

      {analyzing && (
        <div style={{ marginTop: 18, fontFamily: FONT_MONO, fontSize: 12, color: COLORS.mute, lineHeight: 1.8 }}>
          <div>→ helm pull {chart} --version {fromV}</div>
          <div>→ helm pull {chart} --version {toV}</div>
          <div>→ diffing values schema</div>
          <div>→ rendering helm template for both versions</div>
          <div>→ scraping GitHub release notes</div>
          <div>→ <span style={{ color: COLORS.ember }}>GPT-4o synthesizing migration plan…</span></div>
        </div>
      )}
    </Card>
  );
}
