from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import CurrentUser
from app.models.report import Report
from app.schemas.report import ReportCreate, ReportRead
from app.services.reports import ReportError, create_report

router = APIRouter()


def report_http_error(error: ReportError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND
        if error.code.endswith("not_found")
        else status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": str(error)},
    )


@router.post("", response_model=ReportRead, status_code=201)
async def report_content(
    payload: ReportCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ReportRead:
    try:
        report = await create_report(
            session,
            user.id,
            payload.target_type,
            payload.target_id,
            payload.reason,
            payload.details,
        )
    except ReportError as error:
        raise report_http_error(error) from None
    return ReportRead.model_validate(report)


@router.get("/mine", response_model=list[ReportRead])
async def my_reports(
    user: CurrentUser, session: AsyncSession = Depends(get_session)
) -> list[Report]:
    reports = await session.scalars(
        select(Report)
        .where(Report.reporter_id == user.id)
        .order_by(Report.created_at.desc())
        .limit(100)
    )
    return list(reports.all())
