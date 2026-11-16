import { apiGet, apiPost } from "./client";

export interface MetricsReportSummary {
  id: string;
  captured_at: string;
  imported_at: string;
  generator_version: string;
  periods: number;
  contains_names: boolean;
  commits: Record<string, string>;
}

export interface MetricsReportList {
  reports: MetricsReportSummary[];
}

export interface MetricsReportView {
  report: MetricsReportSummary;
  html: string;
}

export function listMetricsReports(repoId: string): Promise<MetricsReportList> {
  return apiGet(`/api/repos/${encodeURIComponent(repoId)}/workspace-metrics`, undefined, { cache: "no-store" });
}

export function getMetricsReport(repoId: string, reportId: string): Promise<MetricsReportView> {
  return apiGet(
    `/api/repos/${encodeURIComponent(repoId)}/workspace-metrics/${encodeURIComponent(reportId)}`,
    undefined, { cache: "no-store" },
  );
}

export function importMetricsReport(repoId: string, evidence: unknown): Promise<MetricsReportSummary> {
  return apiPost(`/api/repos/${encodeURIComponent(repoId)}/workspace-metrics`, evidence);
}
