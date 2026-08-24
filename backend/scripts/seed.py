import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionFactory
from app.models import Category, Listing, ListingCondition, ListingStatus, User
from app.services.embeddings import refresh_listing_embeddings

NAMESPACE = uuid.UUID("d6267f90-d450-4f75-aabc-40eb9f34728e")

CATEGORIES: dict[str, tuple[str, str, list[str]]] = {
    "electronics": (
        "Electronics",
        "desktopcomputer",
        ["Computers", "Monitors", "Audio", "Phones", "Keyboards & Mice", "Chargers & Cables"],
    ),
    "furniture": ("Furniture", "chair.lounge", ["Chairs", "Desks", "Shelving", "Lamps"]),
    "dorm": ("Dorm", "bed.double", ["Mini Fridges", "Fans", "Bedding", "Organizers"]),
    "books": ("Books", "books.vertical", ["Textbooks", "Course Materials", "General Books"]),
    "clothing": ("Clothing", "tshirt", ["Tops", "Bottoms", "Jackets", "Shoes"]),
    "bikes": ("Bikes", "bicycle", ["Bikes", "Scooters", "Helmets", "Accessories"]),
    "kitchen": ("Kitchen", "frying.pan", ["Cookware", "Appliances", "Utensils", "Storage"]),
    "free": ("Free", "gift", []),
}

LISTINGS = [
    ('Dell 27" 4K Monitor', 8500, "electronics", "Monitors", "Kirkland House area", "good"),
    ("Sony WH-1000XM5", 14000, "electronics", "Audio", "Quincy House area", "like_new"),
    ("TI-84 Plus CE", 6000, "electronics", "Other", "Leverett House area", "good"),
    ("Mini Fridge", 4500, "dorm", "Mini Fridges", "Eliot House area", "good"),
    ("IKEA Desk Chair", 3000, "furniture", "Chairs", "Adams House area", "fair"),
    ("Floor Lamp", 0, "free", None, "Cabot House area", "good"),
    ("Standing Desk", 9000, "furniture", "Desks", "Harvard Square", "good"),
    ("Keychron Mechanical Keyboard", 5500, "electronics", "Keyboards & Mice", "SEC", "like_new"),
    ("Calculus Textbook", 2500, "books", "Textbooks", "Smith Campus Center area", "good"),
    ("Road Bike", 12000, "bikes", "Bikes", "Currier House area", "fair"),
    ("Rice Cooker", 2000, "kitchen", "Appliances", "Leverett House area", "good"),
    ("Full-length Mirror", 0, "free", None, "Quincy House area", "good"),
]


def stable_id(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


async def seed() -> None:
    async with SessionFactory() as session:
        category_by_key: dict[str, Category] = {}
        subcategory_by_key: dict[tuple[str, str], Category] = {}
        for order, (slug, (name, symbol, children)) in enumerate(CATEGORIES.items()):
            category = await session.get(Category, stable_id(f"category:{slug}"))
            if category is None:
                category = Category(
                    id=stable_id(f"category:{slug}"),
                    name=name,
                    slug=slug,
                    symbol=symbol,
                    sort_order=order,
                )
                session.add(category)
            category_by_key[slug] = category
            for child_order, child_name in enumerate(children):
                child_slug = child_name.lower().replace(" & ", "-").replace(" ", "-")
                child = await session.get(Category, stable_id(f"category:{slug}:{child_slug}"))
                if child is None:
                    child = Category(
                        id=stable_id(f"category:{slug}:{child_slug}"),
                        parent=category,
                        name=child_name,
                        slug=child_slug,
                        symbol=symbol,
                        sort_order=child_order,
                    )
                    session.add(child)
                subcategory_by_key[(slug, child_name)] = child

        now = datetime.now(UTC)
        seller_ids = [stable_id("seller:maya"), stable_id("seller:theo"), stable_id("seller:alex")]
        seller_names = ["Maya Chen", "Theo Brooks", "Alex Rivera"]
        for seller_id, display_name in zip(seller_ids, seller_names, strict=True):
            if await session.get(User, seller_id) is None:
                session.add(
                    User(
                        id=seller_id,
                        display_name=display_name,
                        harvard_email=f"{display_name.split()[0].lower()}@harvard.edu",
                        email_verified_at=now - timedelta(days=180),
                        terms_accepted_at=now - timedelta(days=180),
                        created_at=now - timedelta(days=180),
                    )
                )
        await session.flush()
        for index, (title, price, category_slug, subcategory_name, zone, condition) in enumerate(
            LISTINGS
        ):
            listing_id = stable_id(f"listing:{title}")
            if await session.scalar(select(Listing.id).where(Listing.id == listing_id)):
                continue
            session.add(
                Listing(
                    id=listing_id,
                    seller_id=seller_ids[index % len(seller_ids)],
                    title=title,
                    description=(
                        f"Campus pickup available near {zone}. Please message to coordinate."
                    ),
                    category=category_by_key[category_slug],
                    subcategory=subcategory_by_key.get((category_slug, subcategory_name or "")),
                    price_cents=price,
                    is_free=price == 0,
                    condition=ListingCondition(condition),
                    status=ListingStatus.ACTIVE,
                    pickup_zone=zone,
                    published_at=now - timedelta(hours=index * 3),
                    save_count=(index * 3) % 11,
                )
            )
        await session.flush()
        await refresh_listing_embeddings(session)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
