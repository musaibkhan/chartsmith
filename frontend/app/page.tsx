"use client";
import { useState, useMemo } from "react";
import { Stepper } from "@/components/Stepper";
import { RepoStep } from "@/components/steps/RepoStep";
import { ChartStep } from "@/components/steps/ChartStep";
import { VersionStep } from "@/components/steps/VersionStep";
import { ValuesStep } from "@/components/steps/ValuesStep";
import { SummaryCard } from "@/components/Report/SummaryCard";
import { UpgradePath } from "@/components/Report/UpgradePath";
import { ResourceChangeCard } from "@/components/Report/ResourceChangeCard";
import { api, AnalyzeReport, ChartInfo, Context } from "@/lib/api";
import { COLORS, FONT_DISPLAY } from "@/lib/theme";

function Logo() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
        <path d="M4 22 L16 4 L28 22 L22 22 L16 13 L10 22 Z"
          stroke={COLORS.ember} strokeWidth="2" strokeLinejoin="round" />
        <path d="M10 22 L16 28 L22 22"
          stroke={COLORS.text} strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 600, letterSpacing: -0.3, fontSize: 18 }}>
        Chart<span style={{ color: COLORS.ember }}>Smith</span>
      </div>
    </div>
  );
}

export default function Home() {
  const [step, setStep]           = useState(0);
  const [repoName, setRepoName]   = useState("grafana-community");
  const [repoUrl, setRepoUrl]     = useState("https://grafana-community.github.io/helm-charts");
  const [charts, setCharts]       = useState<ChartInfo[]>([]);
  const [chart, setChart]         = useState("");
  const [versions, setVersions]   = useState<string[]>([]);
  const [fromV, setFromV]         = useState("");
  const [toV, setToV]             = useState("");
  const [context, setContext]     = useState<Context>("argocd");
  const [wrapper, setWrapper]     = useState("");
  const [values, setValues]       = useState("");
  const [loading, setLoading]     = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [report, setReport]       = useState<AnalyzeReport | null>(null);
  const [filter, setFilter]       = useState<string | null>(null);
  const [error, setError]         = useState<string | null>(null);

  // ── Use report.changes (not report.findings) ──────────────────────────
  const filtered = useMemo(
    () => (!report ? [] : !filter
      ? report.changes
      : report.changes.filter((c) => c.severity === filter)),
    [report, filter],
  );

  const indexRepo = async () => {
    setError(null); setLoading(true);
    try {
      await api.indexRepo(repoName, repoUrl);
      const c = await api.listCharts(repoName);
      setCharts(c);
      setStep(1);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const loadVersions = async () => {
    setError(null); setLoading(true);
    try {
      const { versions } = await api.listVersions(chart);
      setVersions(versions);
      setFromV(versions[versions.length - 1] || "");
      setToV(versions[0] || "");
      setStep(2);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const runAnalyze = async () => {
    setError(null); setAnalyzing(true);
    try {
      const r = await api.analyze({
        chart, from_version: fromV, to_version: toV,
        values_yaml: values, context, wrapper_key: wrapper || null,
      });
      setReport(r); setStep(4);
    } catch (e: any) { setError(e.message); }
    finally { setAnalyzing(false); }
  };

  return (
    <div style={{ minHeight: "100vh", background: COLORS.bg }}>
      <header style={{
        borderBottom: `1px solid ${COLORS.line}`, padding: "16px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        position: "sticky", top: 0, background: COLORS.bg + "F0", backdropFilter: "blur(8px)", zIndex: 10,
      }}>
        <Logo />
        <span style={{ fontSize: 12, color: COLORS.mute }}>v0.1.0</span>
      </header>

      <div style={{ padding: "32px 32px 16px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ fontFamily: FONT_DISPLAY, fontSize: 28, fontWeight: 600, letterSpacing: -0.5, marginBottom: 6 }}>
          Forecast every breaking change <span style={{ color: COLORS.ember }}>before</span> you upgrade.
        </div>
        <div style={{ color: COLORS.mute, fontSize: 14, marginBottom: 24, maxWidth: 640 }}>
          Point ChartSmith at a Helm repo, hand over your <code>values.yaml</code>,
          and get a per-resource migration plan grounded in the real chart diff.
        </div>
        <Stepper step={step} />
      </div>

      <main style={{ maxWidth: 1100, margin: "0 auto", padding: "20px 32px 80px" }}>
        {error && (
          <div style={{
            padding: 14, borderRadius: 8, marginBottom: 16,
            background: "#FF5C7A1A", border: "1px solid #FF5C7A55", color: "#FF5C7A", fontSize: 13,
          }}>{error}</div>
        )}

        {step === 0 && (
          <RepoStep
            repoName={repoName} setRepoName={setRepoName}
            repoUrl={repoUrl} setRepoUrl={setRepoUrl}
            onNext={indexRepo} loading={loading}
          />
        )}
        {step === 1 && (
          <ChartStep charts={charts} chart={chart} setChart={setChart}
            onBack={() => setStep(0)} onNext={loadVersions} />
        )}
        {step === 2 && (
          <VersionStep chart={chart} versions={versions}
            fromV={fromV} setFromV={setFromV} toV={toV} setToV={setToV}
            onBack={() => setStep(1)} onNext={() => setStep(3)} />
        )}
        {step === 3 && (
          <ValuesStep context={context} setContext={setContext}
            wrapper={wrapper} setWrapper={setWrapper}
            values={values} setValues={setValues}
            chart={chart} fromV={fromV} toV={toV}
            onBack={() => setStep(2)} onAnalyze={runAnalyze} analyzing={analyzing} />
        )}
        {step === 4 && report && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <SummaryCard
              report={report}
              filter={filter}
              setFilter={setFilter}
              onBack={() => { setReport(null); setStep(3); }}
            />
            {report.upgrade_path?.length > 0 && (
              <div style={{
                background: COLORS.panel, border: `1px solid ${COLORS.line}`,
                borderRadius: 12, padding: 24,
              }}>
                <UpgradePath path={report.upgrade_path} />
              </div>
            )}
            {filtered.length === 0 ? (
              <div style={{
                padding: 32, textAlign: "center",
                color: COLORS.mute, fontSize: 14,
                background: COLORS.panel, borderRadius: 12,
                border: `1px solid ${COLORS.line}`,
              }}>
                {filter ? `No ${filter} severity changes detected.` : "No changes detected between these versions."}
              </div>
            ) : (
              filtered.map((c, i) => <ResourceChangeCard key={i} change={c} />)
            )}
          </div>
        )}
      </main>
    </div>
  );
}
