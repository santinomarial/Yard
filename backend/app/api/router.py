from fastapi import APIRouter

from app.api.routes import categories, health, listings

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
