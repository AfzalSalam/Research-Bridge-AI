from fastapi import APIRouter

from app.api.v1.routes.demo import router as demo_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.profile import router as profile_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(demo_router)
api_router.include_router(profile_router)
