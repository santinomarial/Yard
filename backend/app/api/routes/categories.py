from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.category import Category
from app.schemas.category import CategoryRead

router = APIRouter()


@router.get("", response_model=list[CategoryRead])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[Category]:
    statement = (
        select(Category)
        .where(Category.parent_id.is_(None), Category.is_active.is_(True))
        .options(selectinload(Category.children))
        .order_by(Category.sort_order, Category.name)
    )
    categories = await session.scalars(statement)
    return list(categories.unique().all())
