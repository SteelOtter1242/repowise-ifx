"""Metadata for explicitly imported, immutable workspace metrics reports."""

from uuid import UUID

from pydantic import BaseModel, Field

from repowise.server.schemas._datetime import UTCDateTime


class MetricsReportSummary(BaseModel):
    id: UUID
    captured_at: UTCDateTime
    imported_at: UTCDateTime
    generator_version: str
    periods: int = Field(ge=0)
    contains_names: bool
    commits: dict[str, str]


class MetricsReportList(BaseModel):
    reports: list[MetricsReportSummary]


class MetricsReportView(BaseModel):
    report: MetricsReportSummary
    html: str
