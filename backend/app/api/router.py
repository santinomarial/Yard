from fastapi import APIRouter

from app.api.routes import (
    admin,
    analytics,
    auth,
    bundles,
    buyer,
    categories,
    health,
    listings,
    messaging,
    notifications,
    pickups,
    reports,
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
api_router.include_router(pickups.router, prefix="/pickups", tags=["pickups"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(admin.router, prefix="/admin", tags=["administration"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
