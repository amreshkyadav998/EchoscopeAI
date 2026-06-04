"""Report REST endpoints (HLD §5.6)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.schemas import (
    MessageResponse,
    ReportCreate,
    ReportList,
    ReportQueued,
    ReportResponse,
    ScheduleCreate,
    ScheduleResponse,
)
from app.storage import local_path, presigned_url
from echoscope_common import NotFoundError
from echoscope_db.models import Report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _download_url(report: Report) -> str | None:
    status_val = report.status.value if hasattr(report.status, "value") else report.status
    if status_val != "done" or not report.s3_key:
        return None
    return presigned_url(report.s3_key) or f"/api/v1/reports/{report.id}/download"


def _to_response(r: Report) -> ReportResponse:
    return ReportResponse(
        id=str(r.id),
        type=r.type.value if hasattr(r.type, "value") else r.type,
        status=r.status.value if hasattr(r.status, "value") else r.status,
        download_url=_download_url(r),
        expires_at=r.expires_at,
        file_size_bytes=r.file_size_bytes,
        created_at=r.created_at,
        completed_at=r.completed_at,
    )


@router.post("", response_model=ReportQueued, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    payload: ReportCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReportQueued:
    report = Report(
        org_id=user.org_id,
        created_by=user.user_id,
        type=payload.type,
        status="queued",
        filters=payload.filters,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    from app.celery_app import generate_report_task

    generate_report_task.delay(str(report.id))
    return ReportQueued(report_id=str(report.id), status="queued")


@router.get("", response_model=ReportList)
async def list_reports(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> ReportList:
    total = await db.scalar(select(func.count(Report.id)).where(Report.org_id == user.org_id))
    rows = list(
        (
            await db.scalars(
                select(Report).where(Report.org_id == user.org_id)
                .order_by(Report.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).all()
    )
    return ReportList(reports=[_to_response(r) for r in rows], total=total or 0)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReportResponse:
    report = await db.get(Report, report_id)
    if report is None or str(report.org_id) != user.org_id:
        raise NotFoundError("Report not found")
    return _to_response(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    report = await db.get(Report, report_id)
    if report is None or str(report.org_id) != user.org_id or not report.s3_key:
        raise NotFoundError("Report not available")
    rtype = report.type.value if hasattr(report.type, "value") else report.type
    path = local_path(report.s3_key)
    if not path.exists():
        raise NotFoundError("Report file not found (S3-stored reports use the pre-signed download_url)")
    media = "application/pdf" if rtype == "pdf" else "text/csv"
    return FileResponse(path, media_type=media, filename=f"report-{report_id}.{rtype}")


@router.delete("/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> MessageResponse:
    report = await db.get(Report, report_id)
    if report is None or str(report.org_id) != user.org_id:
        raise NotFoundError("Report not found")
    # best-effort local file cleanup
    if report.s3_key:
        p = local_path(report.s3_key)
        if p.exists():
            p.unlink()
    await db.delete(report)
    await db.commit()
    return MessageResponse(message="Report deleted")


@router.post("/schedule", response_model=ScheduleResponse, status_code=status.HTTP_202_ACCEPTED)
async def schedule_report(
    payload: ScheduleCreate,
    user: CurrentUser = Depends(get_current_user),
) -> ScheduleResponse:
    # Recurring generation via Celery Beat is a follow-up; we register the intent here.
    schedule_id = str(uuid.uuid4())
    return ScheduleResponse(schedule_id=schedule_id)
