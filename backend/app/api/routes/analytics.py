from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import CurrentUser
from app.schemas.analytics import AnalyticsEventCreate
from app.services.analytics import record_event

router = APIRouter()


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def create_event(
    payload: AnalyticsEventCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        payload.validate_name()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "unsupported_event", "message": "This event is not supported."},
        ) from None
    record_event(
        session,
        payload.name,
        user_id=user.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        properties=payload.properties,
    )
    await session.commit()
    return Response(status_code=status.HTTP_202_ACCEPTED)
