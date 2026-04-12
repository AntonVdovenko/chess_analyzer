"""FastAPI application for Chess Analyzer."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.chess_analyzer.api.routes import router as api_router
from src.chess_analyzer.config import settings

app = FastAPI(
    title="Chess Analyzer",
    description="Analyze chess.com games to identify weaknesses",
    version="0.1.0",
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
