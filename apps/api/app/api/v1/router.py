from fastapi import APIRouter

from app.api.v1.routes.account import router as account_router
from app.api.v1.routes.account_profile import router as account_profile_router
from app.api.v1.routes.applications import router as applications_router
from app.api.v1.routes.contact import router as contact_router
from app.api.v1.routes.demo import router as demo_router
from app.api.v1.routes.discovery import router as discovery_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.mentor_discovery import router as mentor_discovery_router
from app.api.v1.routes.opportunities import router as opportunities_router
from app.api.v1.routes.outreach import router as outreach_router
from app.api.v1.routes.profile import router as profile_router
from app.api.v1.routes.research import router as research_router
from app.api.v1.routes.university import router as university_router
from app.api.v1.routes.workflow import router as workflow_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(demo_router)
api_router.include_router(discovery_router)
api_router.include_router(mentor_discovery_router)
api_router.include_router(outreach_router)
api_router.include_router(opportunities_router)
api_router.include_router(applications_router)
api_router.include_router(account_profile_router)
api_router.include_router(account_router)
api_router.include_router(profile_router)
api_router.include_router(workflow_router)

api_router.include_router(university_router)

api_router.include_router(contact_router)


api_router.include_router(research_router)

api_router.include_router(documents_router)
