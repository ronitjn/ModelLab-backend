"""Mock lip-sync service for processing tasks.

Provides asynchronous background processing simulation and task state tracking.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal, Optional

from app.schemas.processing import ModelChoice
from app.models.manager import DEFAULT_MANAGER
from concurrent.futures import ThreadPoolExecutor
import functools


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

        # Simulate model loading and inference using the ModelManager.
        try:
            model = DEFAULT_MANAGER.get(model_choice.value)
        except KeyError:
            # If model isn't registered treat as processing failure; for now
            # we'll still create a stub result so API consumers can be tested.
            model = None

        # Simulate computation delay (replace with real inference in future)
        await asyncio.sleep(2.0)

        # If model is callable, run it. It may perform blocking work (subprocess)
        # so execute in a threadpool. If it returns a path to an output file,
        # use that as the final result. On any error, fall back to the mock file.
        result_path: Optional[Path] = None

        if callable(model):
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as pool:
                func = functools.partial(model, task_id=task_id, video=str(video_path), audio=str(audio_path))
                try:
                    returned = await loop.run_in_executor(pool, func)
                    if isinstance(returned, str):
                        p = Path(returned)
                        if p.exists():
                            result_path = p
                except Exception:
                    # Adapter failed; we'll fallback to mock result below
                    pass

        # If model didn't produce a real result, create a mock placeholder
        if not result_path:
            result_path = cls._results_dir / f"{task_id}.mp4"
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
