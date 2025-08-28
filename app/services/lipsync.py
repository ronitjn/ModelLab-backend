"""Mock lip-sync service for processing tasks.

Provides asynchronous background processing simulation and task state tracking.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal, Optional

from app.schemas.processing import ModelChoice


Status = Literal["processing", "finished"]


@dataclass
class TaskInfo:
    """Internal representation of a processing task."""

    task_id: str
    video_path: Path
    audio_path: Path
    model_choice: ModelChoice
    status: Status = "processing"
    result_path: Optional[Path] = None


class LipSyncService:
    """Service to manage mock lip-sync processing tasks."""

    _tasks: Dict[str, TaskInfo] = {}
    _results_dir: Path = Path("/tmp/uploads/results")
    _results_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    async def process_task(
        cls, task_id: str, video_path: Path, audio_path: Path, model_choice: ModelChoice
    ) -> None:
        """Simulate asynchronous processing and produce a mock mp4 file.

        Args:
            task_id: Unique identifier for the task.
            video_path: Path to the uploaded video file.
            audio_path: Path to the uploaded audio file.
            model_choice: Selected model variant.
        """
        # Register task
        info = TaskInfo(task_id, video_path, audio_path, model_choice)
        cls._tasks[task_id] = info

        # Simulate computation delay
        await asyncio.sleep(2.0)

        # Generate a mock result file
        result_path = cls._results_dir / f"{task_id}.mp4"
        # Create a tiny placeholder mp4-like file (not a real video but sufficient for IO tests)
        result_path.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")

        info.result_path = result_path
        info.status = "finished"

    @classmethod
    def get_status(cls, task_id: str) -> Status:
        """Get the current status of a task.

        Args:
            task_id: Identifier of the task.

        Returns:
            Task status: "processing" or "finished". Unknown tasks are treated as processing
            until they are registered/created.
        """
        info = cls._tasks.get(task_id)
        if not info:
            return "processing"
        return info.status

    @classmethod
    def get_result_path(cls, task_id: str) -> Path:
        """Get the path to the result file for a task."""
        info = cls._tasks.get(task_id)
        if info and info.result_path:
            return info.result_path
        return cls._results_dir / f"{task_id}.mp4"
