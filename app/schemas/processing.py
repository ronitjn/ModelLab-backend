"""Pydantic schemas and enums for processing endpoints."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ModelChoice(str, Enum):
    """Available ML model choices."""

    model1 = "model1"
    model2 = "model2"
    model3 = "model3"


class ProcessResponse(BaseModel):
    """Response model for a submitted processing task."""

    task_id: str = Field(..., description="Unique identifier for the processing task")


class ResultStatusResponse(BaseModel):
    """Response model for task status when result isn't ready."""

    status: str = Field(..., description='Current status: "processing" or "finished"')
