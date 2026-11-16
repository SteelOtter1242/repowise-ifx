"""Metadata for explicitly imported, immutable workspace metrics reports."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MetricsReportSummary(BaseModel):
    id: UUID
    captured_at: datetime
    imported_at: datetime
    generator_version: str
    periods: int = Field(ge=0)
    contains_names: bool
    commits: dict[str, str]


class MetricsReportList(BaseModel):
    reports: list[MetricsReportSummary]


class MetricsReportView(BaseModel):
    report: MetricsReportSummary
    html: str
