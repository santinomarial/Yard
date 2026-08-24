from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.category import Category
from app.schemas.category import CategoryRead

router = APIRouter()


@router.get("", response_model=list[CategoryRead])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[CategoryRead]:
    statement = (
        select(Category)
        .where(Category.parent_id.is_(None), Category.is_active.is_(True))
        .options(selectinload(Category.children))
        .order_by(Category.sort_order, Category.name)
    )
    categories = await session.scalars(statement)
    return [
        CategoryRead(
            id=category.id,
            name=category.name,
            slug=category.slug,
            symbol=category.symbol,
            sort_order=category.sort_order,
            children=[
                CategoryRead(
                    id=child.id,
                    name=child.name,
                    slug=child.slug,
                    symbol=child.symbol,
                    sort_order=child.sort_order,
                    children=[],
                )
                for child in sorted(
                    category.children, key=lambda item: (item.sort_order, item.name)
                )
                if child.is_active
            ],
        )
        for category in categories.unique().all()
    ]
