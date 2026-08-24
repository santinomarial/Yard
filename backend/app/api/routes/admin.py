import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import AdminUser
from app.models.listing import Listing, ListingStatus
from app.models.report import (
    AdminAction,
    Report,
    ReportReason,
    ReportStatus,
    ReportTarget,
)
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User
from app.schemas.report import (
    AdminActionRead,
    AdminDashboard,
    AdminResolution,
    ReportRead,
)
from app.services.reports import ReportError, resolve_report

router = APIRouter()


def admin_http_error(error: ReportError) -> HTTPException:
    if error.code.endswith("not_found"):
        code = status.HTTP_404_NOT_FOUND
    else:
        code = status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=code,
        detail={"code": error.code, "message": str(error)},
    )


async def count(session: AsyncSession, statement) -> int:  # type: ignore[no-untyped-def]
    return int(await session.scalar(statement) or 0)


@router.get("/dashboard", response_model=AdminDashboard)
async def dashboard(
    _admin: AdminUser, session: AsyncSession = Depends(get_session)
) -> AdminDashboard:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return AdminDashboard(
        open_reports=await count(
            session,
            select(func.count()).select_from(Report).where(Report.status == ReportStatus.OPEN),
        ),
        reports_resolved_today=await count(
            session,
            select(func.count()).select_from(Report).where(Report.resolved_at >= today),
        ),
        active_listings=await count(
            session,
            select(func.count()).select_from(Listing).where(Listing.status == ListingStatus.ACTIVE),
        ),
        new_users_today=await count(
            session,
            select(func.count()).select_from(User).where(User.created_at >= today),
        ),
        completed_exchanges=await count(
            session,
            select(func.count())
            .select_from(Reservation)
            .where(Reservation.status == ReservationStatus.COMPLETED),
        ),
        moderation_backlog=await count(
            session,
            select(func.count())
            .select_from(Listing)
            .where(Listing.status == ListingStatus.PENDING_MODERATION),
        ),
    )


@router.get("/reports", response_model=list[ReportRead])
async def reports(
    _admin: AdminUser,
    target_type: ReportTarget | None = None,
    reason: ReportReason | None = None,
    report_status: ReportStatus | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[Report]:
    statement = select(Report)
    if target_type:
        statement = statement.where(Report.target_type == target_type)
    if reason:
        statement = statement.where(Report.reason == reason)
    if report_status:
        statement = statement.where(Report.status == report_status)
    rows = await session.scalars(statement.order_by(Report.created_at.desc()).limit(200))
    return list(rows.all())


@router.get("/reports/{report_id}", response_model=ReportRead)
async def report_detail(
    report_id: uuid.UUID,
    _admin: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Not found")
    return report


@router.post("/reports/{report_id}/resolve", response_model=ReportRead)
async def resolve(
    report_id: uuid.UUID,
    payload: AdminResolution,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session),
) -> ReportRead:
    try:
        report = await resolve_report(session, report_id, admin.id, payload.action, payload.notes)
    except ReportError as error:
        raise admin_http_error(error) from None
    return ReportRead.model_validate(report)


@router.get("/audit-log", response_model=list[AdminActionRead])
async def audit_log(
    _admin: AdminUser, session: AsyncSession = Depends(get_session)
) -> list[AdminAction]:
    rows = await session.scalars(
        select(AdminAction).order_by(AdminAction.created_at.desc()).limit(200)
    )
    return list(rows.all())
