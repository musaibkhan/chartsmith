const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = `${BASE}/api/v1`;

export type ChartInfo = { name: string; description: string; latest_version: string };
export type Severity = "critical" | "high" | "medium" | "safe";
export type Context  = "plain" | "argocd" | "umbrella" | "helmfile";

export type Finding = {
  severity: Severity; key: string; title: string;
  yours: string; fix: string; note?: string | null; since?: string | null;
};

export type AnalyzeReport = {
  chart: string; from_version: string; to_version: string;
  wrapper_key: string | null; context: Context;
  stats: { critical: number; high: number; medium: number; safe: number; total_keys: number };
  upgrade_path: string[]; findings: Finding[];
};

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  indexRepo: (name: string, url: string) =>
    fetch(`${API}/repos/index`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, url }),
    }).then(j),

  listCharts: (repo: string) =>
    fetch(`${API}/charts?repo=${encodeURIComponent(repo)}`).then(j<ChartInfo[]>),

  listVersions: (chart: string) => {
    const [repo, name] = chart.split("/");
    return fetch(`${API}/charts/${repo}/${name}/versions`).then(j<{ chart: string; versions: string[] }>);
  },

  analyze: (body: {
    chart: string; from_version: string; to_version: string;
    values_yaml: string; context: Context; wrapper_key?: string | null;
  }) =>
    fetch(`${API}/analyze`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<AnalyzeReport>),
};
