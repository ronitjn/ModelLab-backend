"""
ModelLab FastAPI application entrypoint.

This module initializes the FastAPI app, configures CORS, and includes API routers.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.processing import router as processing_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI instance.
    """
    app = FastAPI(title="ModelLab Backend", version="0.1.0")

    # Configure CORS for frontend access; adjust origins as needed.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers without prefix to match required paths
    app.include_router(processing_router, tags=["processing"])

    return app


app = create_app()
