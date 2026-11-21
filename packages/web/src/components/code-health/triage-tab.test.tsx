// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  data: undefined as { points: never[]; total: number; latest_change_at?: string | null } | undefined,
}));

vi.mock("swr", () => ({
  default: () => ({ data: state.data, isLoading: !state.data }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/repos/r",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@repowise-dev/ui/health", () => ({
  TriageView: ({ leadSlot }: { leadSlot: React.ReactNode }) => leadSlot,
}));
vi.mock("@/components/code-health/fix-first-section", () => ({
  FixFirstSection: () => null,
}));
vi.mock("./area-rail-labels", () => ({ useAreaRailLabels: () => ({}) }));
vi.mock("./use-include-param", () => ({ useIncludeParam: () => [[], vi.fn()] }));

import { TriageTab } from "./triage-tab";

afterEach(() => {
  cleanup();
  state.data = undefined;
});

it("shows the latest indexed change when the churn lens has no points", () => {
  state.data = { points: [], total: 0, latest_change_at: "2026-07-01T00:00:00+00:00" };
  render(<TriageTab repoId="r" overlay="churn" />);
  expect(screen.getByRole("status").textContent).toContain("latest indexed change 2026-07-01");
});

it("does not claim there is no history when the latest change is unknown", () => {
  state.data = { points: [], total: 0, latest_change_at: null };
  render(<TriageTab repoId="r" overlay="churn" />);
  expect(screen.getByRole("status").textContent).toBe("No recent churn data for scored files");
});

it("does not show the notice for another lens or while loading", () => {
  state.data = { points: [], total: 0, latest_change_at: null };
  const { rerender } = render(<TriageTab repoId="r" overlay="health" />);
  expect(screen.queryByRole("status")).toBeNull();
  state.data = undefined;
  rerender(<TriageTab repoId="r" overlay="churn" />);
  expect(screen.queryByRole("status")).toBeNull();
});
