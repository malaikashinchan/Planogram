"""
API v1 router aggregator.

Phase 9:  /auth
Phase 10: /organizations, /users, /stores, /products, /planograms, /audits
"""

from fastapi import APIRouter

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.organizations import router as organizations_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.stores import router as stores_router
from backend.app.api.v1.products import router as products_router
from backend.app.api.v1.planograms import router as planograms_router
from backend.app.api.v1.audits import router as audits_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(users_router)
api_router.include_router(stores_router)
api_router.include_router(products_router)
api_router.include_router(planograms_router)
api_router.include_router(audits_router)
