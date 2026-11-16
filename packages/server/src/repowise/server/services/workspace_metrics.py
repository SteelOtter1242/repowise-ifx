"""Import saved metrics evidence without indexing or reading arbitrary files."""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from repowise.core.report.render import report_renderers
from repowise.server.schemas.workspace_metrics import MetricsReportSummary, MetricsReportView


class MetricsRendererUnavailableError(RuntimeError):
    pass


def _store_root() -> Path:
    return Path.home() / ".repowise" / "metrics-reports"


def _repository_dir(repo_id: str) -> Path:
    return _store_root() / hashlib.sha256(repo_id.encode()).hexdigest()


def import_report(
    repo_id: str,
    repository_path: str,
    document: dict[str, Any],
) -> MetricsReportSummary:
    try:
        renderer = report_renderers.get("metrics-html")
    except KeyError as exc:
        raise MetricsRendererUnavailableError(
            "Install the repowise-workspace-metrics extension in the server environment "
            "and restart Repowise before importing a report."
        ) from exc

    try:
        if document["generator"]["name"] != "repowise-workspace-metrics":
            raise ValueError("Expected workspace metrics JSON evidence, not HTML or another report")
        aliases = document["aliases"]
        base = Path(repository_path).resolve()
        if not aliases or any(
            not Path(alias["path"]).resolve().is_relative_to(base) for alias in aliases
        ):
            raise ValueError("Every report alias must belong to this repository's checkout")
        rendered = renderer(document)
        metadata = MetricsReportSummary(
            id=uuid4(),
            captured_at=document["generated_at"],
            imported_at=datetime.now(UTC),
            generator_version=document["generator"]["version"],
            periods=len(document.get("history", {}).get("points", [])),
            contains_names="mapped_display_names"
            in document.get("ownership", {}).get("identity_label_modes", []),
            commits={alias["alias"]: alias["head"] for alias in aliases},
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid workspace metrics JSON evidence") from exc

    directory = _repository_dir(repo_id)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".import-", dir=directory) as temporary:
        staged = Path(temporary)
        (staged / "evidence.json").write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )
        (staged / "report.html").write_text(rendered, encoding="utf-8")
        (staged / "metadata.json").write_text(metadata.model_dump_json(), encoding="utf-8")
        staged.replace(directory / metadata.id.hex)
    return metadata


def list_reports(repo_id: str) -> list[MetricsReportSummary]:
    directory = _repository_dir(repo_id)
    if not directory.exists():
        return []
    reports = [
        MetricsReportSummary.model_validate_json(
            (path / "metadata.json").read_text(encoding="utf-8")
        )
        for path in directory.iterdir()
        if not path.name.startswith(".import-")
    ]
    return sorted(reports, key=lambda report: report.imported_at, reverse=True)


def read_report(repo_id: str, report_id: UUID) -> MetricsReportView:
    directory = _repository_dir(repo_id) / report_id.hex
    if not directory.exists():
        raise LookupError("Metrics report not found")
    return MetricsReportView(
        report=MetricsReportSummary.model_validate_json(
            (directory / "metadata.json").read_text(encoding="utf-8")
        ),
        html=(directory / "report.html").read_text(encoding="utf-8"),
    )
