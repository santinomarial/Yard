import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.main import app
from app.models import Category, Listing, ListingCondition, ListingStatus


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(session: AsyncSession) -> AsyncSession:
    electronics = Category(name="Electronics", slug="electronics", symbol="desktopcomputer")
    furniture = Category(name="Furniture", slug="furniture", symbol="chair.lounge")
    session.add_all([electronics, furniture])
    await session.flush()
    session.add_all(
        [
            Listing(
                seller_id=uuid.uuid4(),
                title='Dell 27" Monitor',
                description="A sharp second screen for coding.",
                category=electronics,
                price_cents=8500,
                is_free=False,
                condition=ListingCondition.GOOD,
                status=ListingStatus.ACTIVE,
                pickup_zone="Kirkland House area",
                published_at=datetime.now(UTC),
            ),
            Listing(
                seller_id=uuid.uuid4(),
                title="Walnut Desk",
                description="Compact dorm desk.",
                category=furniture,
                price_cents=0,
                is_free=True,
                condition=ListingCondition.FAIR,
                status=ListingStatus.ACTIVE,
                pickup_zone="Harvard Square",
                published_at=datetime.now(UTC),
            ),
            Listing(
                seller_id=uuid.uuid4(),
                title="Archived Keyboard",
                description="No longer available.",
                category=electronics,
                price_cents=3000,
                is_free=False,
                condition=ListingCondition.GOOD,
                status=ListingStatus.ARCHIVED,
                pickup_zone="SEC",
            ),
        ]
    )
    await session.commit()
    return session


@pytest_asyncio.fixture
async def client(seeded_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield seeded_session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
