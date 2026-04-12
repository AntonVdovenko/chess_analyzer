"""API routes for Chess Analyzer."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """Root API endpoint."""
    return {"message": "Chess Analyzer API"}
