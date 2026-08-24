from fastapi import APIRouter

from app.api.routes import (
    auth,
    bundles,
    buyer,
    categories,
    health,
    listings,
    messaging,
    reservations,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
api_router.include_router(buyer.router, tags=["buyer"])
api_router.include_router(bundles.router, prefix="/bundles", tags=["bundles"])
api_router.include_router(messaging.router, tags=["messaging"])
