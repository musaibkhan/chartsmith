"use client";
import { Card, Field, Button, inputStyle } from "../ui";
import { FONT_DISPLAY, COLORS } from "@/lib/theme";

export function RepoStep({ repoName, setRepoName, repoUrl, setRepoUrl, onNext, loading }: any) {
  return (
    <Card>
      <div style={{ fontFamily: FONT_DISPLAY, fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
        Add a Helm repository
      </div>
      <div style={{ color: COLORS.mute, fontSize: 13, marginBottom: 20 }}>
        We run <code>helm repo add</code> and index every chart and version.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16 }}>
        <Field label="Repo name">
          <input style={inputStyle} value={repoName} onChange={(e: any) => setRepoName(e.target.value)} />
        </Field>
        <Field label="Repo URL">
          <input style={inputStyle} value={repoUrl} onChange={(e: any) => setRepoUrl(e.target.value)} />
        </Field>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Button primary onClick={onNext} disabled={loading || !repoName || !repoUrl}>
          {loading ? "Indexing…" : "Index repo →"}
        </Button>
      </div>
    </Card>
  );
}
