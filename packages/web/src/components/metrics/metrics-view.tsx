"use client";

import { useId, useState, type ChangeEvent } from "react";
import { useTranslations } from "next-intl";
import useSWR from "swr";
import { ApiError } from "@repowise-dev/ui/shared/api-error";
import {
  getMetricsReport,
  importMetricsReport,
  listMetricsReports,
} from "@/lib/api/workspace-metrics";

export function MetricsView({ repoId }: { repoId: string }) {
  const t = useTranslations("views.metrics");
  const inputId = useId();
  const [selected, setSelected] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const { data, error, isLoading, mutate } = useSWR(
    ["workspace-metrics", repoId], () => listMetricsReports(repoId),
  );
  const reports = data?.reports ?? [];
  const reportId = reports.some((report) => report.id === selected) ? selected : reports[0]?.id;
  const { data: view, error: viewError, isLoading: viewLoading, mutate: reloadView } = useSWR(
    reportId ? ["workspace-metrics-report", repoId, reportId] : null,
    reportId ? () => getMetricsReport(repoId, reportId) : null,
    { revalidateOnFocus: false },
  );

  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportError("");
    try {
      const evidence: unknown = JSON.parse(await file.text());
      const imported = await importMetricsReport(repoId, evidence);
      setSelected(imported.id);
      await mutate();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : t("importFailed"));
    } finally {
      setImporting(false);
      input.value = "";
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--color-text-secondary)]">{t("privacy")}</p>
      <details className="rounded-lg border border-[var(--color-border)] p-4" open={reports.length === 0}>
        <summary className="cursor-pointer font-medium">{t("importTitle")}</summary>
        <p className="my-3 text-sm text-[var(--color-text-secondary)]">{t("importHelp")}</p>
        <label htmlFor={inputId} className="block text-sm">{t("chooseJson")}</label>
        <input id={inputId} type="file" accept=".json,application/json" disabled={importing} onChange={(event) => void importFile(event)} />
        {importing && <p role="status">{t("importing")}</p>}
        <p className="mt-3 text-sm">{t("serverImport")}</p>
        <code className="block overflow-x-auto text-xs">POST /api/repos/{repoId}/workspace-metrics</code>
      </details>
      {importError && <ApiError title={t("importFailed")} message={importError} />}
      {error ? (
        <ApiError title={t("loadFailed")} message={error instanceof Error ? error.message : t("loadFailed")} onRetry={() => void mutate()} retryLabel={t("retry")} />
      ) : isLoading ? (
        <p role="status">{t("loading")}</p>
      ) : reports.length === 0 ? (
        <p>{t("empty")}</p>
      ) : (
        <>
          <label className="block text-sm">
            {t("report")}
            <select className="ml-3 max-w-full rounded border p-2 text-[var(--color-text-primary)] bg-[var(--color-bg-primary)]" value={reportId} onChange={(event) => setSelected(event.target.value)}>
              {reports.map((report) => (
                <option key={report.id} value={report.id}>
                  {report.captured_at} · {t("periods", { count: report.periods })}
                </option>
              ))}
            </select>
          </label>
          {viewError ? (
            <ApiError title={t("loadFailed")} message={viewError instanceof Error ? viewError.message : t("loadFailed")} onRetry={() => void reloadView()} retryLabel={t("retry")} />
          ) : viewLoading || !view ? (
            <p role="status">{t("loading")}</p>
          ) : (
            <>
              <p className="text-xs text-[var(--color-text-secondary)]">
                {t("savedSnapshot", { version: view.report.generator_version })}{" "}
                {Object.entries(view.report.commits).map(([alias, head]) => `${alias}: ${head.slice(0, 12)}`).join(", ")}
              </p>
              <iframe
                key={view.report.id}
                title={t("frameTitle")}
                srcDoc={view.html}
                sandbox="allow-scripts"
                referrerPolicy="no-referrer"
                className="min-h-[1000px] w-full rounded-lg border bg-white"
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
