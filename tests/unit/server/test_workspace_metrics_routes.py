"""Saved reports are explicitly imported, repository-scoped and persistent."""

from __future__ import annotations

import copy

import pytest

from repowise.core.report.render import report_renderers
from repowise.server.routers import workspace_metrics
from repowise.server.services import workspace_metrics as saved
from tests.unit.server.conftest import create_test_repo

pytestmark = pytest.mark.anyio


@pytest.fixture
async def metrics_client(app, client, tmp_path, monkeypatch):
    app.include_router(workspace_metrics.router)
    monkeypatch.setattr(saved, "_store_root", lambda: tmp_path / "saved-reports")
    return client


@pytest.fixture
def renderer(monkeypatch):
    def render(document):
        if document.get("invalid"):
            raise ValueError("Counter totals do not reconcile")
        return "<!doctype html><h1>Charts</h1><script>document.body.dataset.ready='yes'</script>"

    monkeypatch.setattr(report_renderers, "get", lambda name: render)
    return render


def _evidence(repo):
    return {
        "generator": {"name": "repowise-workspace-metrics", "version": "0.4.2"},
        "generated_at": "2026-11-16T02:00:00+00:00",
        "aliases": [{"alias": "pilot", "path": repo["local_path"], "head": "a" * 40}],
        "ownership": {"identity_label_modes": ["mapped_display_names"]},
    }


async def test_import_persists_report_without_indexing(metrics_client, tmp_path, renderer):
    repo = await create_test_repo(metrics_client, tmp_path)
    url = f"/api/repos/{repo['id']}/workspace-metrics"
    assert (await metrics_client.get(url)).json() == {"reports": []}
    response = await metrics_client.post(url, json=_evidence(repo))
    assert response.status_code == 201
    metadata = response.json()
    assert metadata["contains_names"] is True
    assert response.headers["cache-control"] == "private, no-store"
    report = await metrics_client.get(f"{url}/{metadata['id']}")
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("application/json")
    assert report.headers["cache-control"] == "private, no-store"
    assert report.json()["html"] == renderer(_evidence(repo))
    assert (await metrics_client.get(url)).json()["reports"] == [metadata]
    assert (await metrics_client.get(f"/api/repos/{repo['id']}/files")).json()["files"] == []


async def test_import_rejects_unrelated_aliases_and_invalid_evidence(
    metrics_client, tmp_path, renderer
):
    repo = await create_test_repo(metrics_client, tmp_path)
    url = f"/api/repos/{repo['id']}/workspace-metrics"
    evidence = _evidence(repo)
    evidence["aliases"][0]["path"] = str(tmp_path / "unrelated")
    assert (await metrics_client.post(url, json=evidence)).status_code == 400
    invalid = copy.deepcopy(_evidence(repo))
    invalid["invalid"] = True
    assert (await metrics_client.post(url, json=invalid)).status_code == 400
    assert (await metrics_client.post(url, json={"generator": "malformed"})).status_code == 400
    assert (await metrics_client.get(url)).json() == {"reports": []}


async def test_reports_require_authentication(metrics_client, monkeypatch):
    import repowise.server.deps as deps

    monkeypatch.setattr(deps, "_API_KEY", "metrics-test-key")
    url = "/api/repos/test/workspace-metrics"
    assert (await metrics_client.get(url)).status_code == 401
    assert (await metrics_client.post(url, json={})).status_code == 401
    assert (await metrics_client.get(f"{url}/{'0' * 32}")).status_code == 401


async def test_unknown_reports_and_missing_renderer_are_explicit(
    metrics_client, tmp_path, monkeypatch
):
    repo = await create_test_repo(metrics_client, tmp_path)
    url = f"/api/repos/{repo['id']}/workspace-metrics"
    assert (await metrics_client.get(f"{url}/{'0' * 32}")).status_code == 404
    assert (await metrics_client.get(f"{url}/not-a-report-id")).status_code == 422

    def unavailable(name):
        raise KeyError(name)

    monkeypatch.setattr(report_renderers, "get", unavailable)
    result = await metrics_client.post(url, json=_evidence(repo))
    assert result.status_code == 503
    assert "Install" in result.json()["detail"]
