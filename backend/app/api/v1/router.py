"""
API v1 router aggregator.

Phase 9:  /auth
Phase 10: /users, /organizations, /stores, /products, /planograms, /audits
"""

from fastapi import APIRouter

from backend.app.api.v1.auth import router as auth_router

api_router = APIRouter()

api_router.include_router(auth_router)
