# app/api/router.py

from fastapi import APIRouter
from app.api.ingest import router as ingest_router
from app.api.solve import router as solve_router
from app.api.feedback import router as feedback_router

router = APIRouter(prefix="/api/v1")

router.include_router(ingest_router, tags=["ingest"])
router.include_router(solve_router, tags=["solve"])
router.include_router(feedback_router, tags=["feedback"])

