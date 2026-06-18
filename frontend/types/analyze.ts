/**
 * types/analyze.ts - TypeScript types for chart analysis
 */

export type Severity = "critical" | "high" | "medium" | "safe";
export type ChangeType = "added" | "removed" | "modified" | "deprecated_api";
export type Context = "plain" | "argocd" | "umbrella" | "helmfile";

/**
 * A single resource change detected in manifest diff.
 */
export interface ResourceChange {
  severity: Severity;
  change_type: ChangeType;
  kind: string;
  name: string;
  namespace: string;
  api_version_old: string | null;
  api_version_new: string | null;
  title: string;
  old_yaml: string;
  new_yaml: string;
  note: string | null;
}

/**
 * Statistics about changes by severity.
 */
export interface ReportStats {
  critical: number;
  high: number;
  medium: number;
  safe: number;
  total_changes: number;
}

/**
 * Suggested intermediate upgrade version.
 */
export interface UpgradePath {
  description: string;
  intermediate_version: string;
}

/**
 * Complete analysis report returned by /api/v1/analyze
 */
export interface AnalyzeReport {
  chart: string;
  from_version: string;
  to_version: string;
  wrapper_key: string | null;
  context: Context;
  stats: ReportStats;
  changes: ResourceChange[];
  upgrade_path: UpgradePath[];
  summary: string;
}

/**
 * Request payload for /api/v1/analyze
 */
export interface AnalyzeRequestPayload {
  chart: string;
  from_version: string;
  to_version: string;
  values_yaml: string;
  context?: Context;
  wrapper_key?: string | null;
}