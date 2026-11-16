// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SWRConfig } from "swr";
import { MetricsView } from "./metrics-view";

const api = vi.hoisted(() => ({
  listMetricsReports: vi.fn(),
  getMetricsReport: vi.fn(),
  importMetricsReport: vi.fn(),
}));
vi.mock("@/lib/api/workspace-metrics", () => api);

function show() {
  return render(
    <SWRConfig value={{ provider: () => new Map(), shouldRetryOnError: false }}>
      <MetricsView repoId="r1" />
    </SWRConfig>,
  );
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("saved metrics reports", () => {
  it("opens the latest saved chart report in an isolated frame, not an evidence table", async () => {
    const report = {
      id: "report-1", captured_at: "2026-11-16T02:00:00Z", imported_at: "2026-11-16T03:00:00Z",
      generator_version: "0.4.2", periods: 12, contains_names: true, commits: { pilot: "a".repeat(40) },
    };
    const html = "<!doctype html><h1>Measured charts</h1>";
    api.listMetricsReports.mockResolvedValue({ reports: [report] });
    api.getMetricsReport.mockResolvedValue({ report, html });
    show();
    const frame = await screen.findByTitle("Workspace metrics charts");
    expect(api.getMetricsReport).toHaveBeenCalledWith("r1", "report-1");
    expect(frame.getAttribute("srcdoc")).toBe(html);
    expect(frame.getAttribute("sandbox")).toBe("allow-scripts");
    expect(frame.getAttribute("referrerpolicy")).toBe("no-referrer");
    expect(screen.queryAllByRole("table")).toHaveLength(0);
  });

  it("explains explicit import when no report exists and does not request imaginary reports", async () => {
    api.listMetricsReports.mockResolvedValue({ reports: [] });
    show();
    await screen.findByText("No metrics report has been imported for this repository yet.");
    expect(api.getMetricsReport).not.toHaveBeenCalled();
    expect(screen.getByText("Import a saved metrics report")).toBeTruthy();
  });

  it("surfaces API and import errors instead of showing an empty success state", async () => {
    api.listMetricsReports.mockRejectedValue(new Error("Not authorized"));
    api.importMetricsReport.mockRejectedValue(new Error("Install the metrics extension"));
    show();
    await screen.findByText("Not authorized");
    expect(screen.queryByText("No metrics report has been imported for this repository yet.")).toBeNull();
    const file = new File(["{}"], "snapshot.json", { type: "application/json" });
    Object.defineProperty(file, "text", { value: async () => "{}" });
    fireEvent.change(screen.getByLabelText("Metrics evidence JSON"), { target: { files: [file] } });
    await waitFor(() => expect(api.importMetricsReport).toHaveBeenCalledWith("r1", {}));
    await screen.findByText("Install the metrics extension");
    expect(screen.queryByTitle("Workspace metrics charts")).toBeNull();
  });
});
