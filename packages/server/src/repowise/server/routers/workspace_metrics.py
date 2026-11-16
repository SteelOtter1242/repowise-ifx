"""Authenticated saved-report import and viewing; never a source-file endpoint."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from repowise.core.persistence import crud
from repowise.server.deps import get_db_session, verify_api_key
from repowise.server.schemas.workspace_metrics import (
    MetricsReportList,
    MetricsReportSummary,
    MetricsReportView,
)
from repowise.server.services import workspace_metrics as saved

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/repos/{repo_id}/workspace-metrics",
    tags=["workspace-metrics"],
    dependencies=[Depends(verify_api_key)],
)


async def _repository(repo_id: str, session: AsyncSession):
    repo = await crud.get_repository(session, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def _storage_error() -> HTTPException:
    logger.exception("metrics_report_storage_failed")
    return HTTPException(status_code=500, detail="Cannot access saved metrics reports")


@router.get("", response_model=MetricsReportList)
async def list_reports(
    repo_id: str,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> MetricsReportList:
    await _repository(repo_id, session)
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return MetricsReportList(reports=await run_in_threadpool(saved.list_reports, repo_id))
    except (OSError, ValidationError) as exc:
        raise _storage_error() from exc


@router.post("", response_model=MetricsReportSummary, status_code=201)
async def import_report(
    repo_id: str,
    document: dict[str, Any],
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> MetricsReportSummary:
    repo = await _repository(repo_id, session)
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return await run_in_threadpool(saved.import_report, repo_id, repo.local_path, document)
    except saved.MetricsRendererUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OSError as exc:
        raise _storage_error() from exc


@router.get("/{report_id}", response_model=MetricsReportView)
async def read_report(
    repo_id: str,
    report_id: UUID,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> MetricsReportView:
    await _repository(repo_id, session)
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return await run_in_threadpool(saved.read_report, repo_id, report_id)
    except (OSError, ValidationError) as exc:
        raise _storage_error() from exc
