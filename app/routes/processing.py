"""
Processing routes for ModelLab lip-syncing service.

Defines endpoints to submit a processing task and retrieve results.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.schemas.processing import (
    ModelChoice,
    ProcessResponse,
    ResultStatusResponse,
)
from app.services.lipsync import LipSyncService

UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


async def _save_upload(file: UploadFile, dest: Path) -> None:
    """Save an uploaded file asynchronously to the specified destination.

    Args:
        file: The uploaded file to save.
        dest: The destination path.
    """
    async with aiofiles.open(dest, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await out.write(chunk)


@router.post("/process/", response_model=ProcessResponse)
async def process_media(
    background_tasks: BackgroundTasks,
    video_file: Annotated[UploadFile, File(description="Input video file (mp4)")],
    audio_file: Annotated[
        UploadFile, File(description="Target audio file (wav/mp3)")
    ],
    model_choice: ModelChoice,
):
    """Submit a new lip-sync processing task.

    Saves uploaded files to temporary storage and schedules background processing.

    Returns:
        A JSON response containing the generated task ID.
    """
    # Validate content types
    if video_file.content_type not in {"video/mp4"}:
        raise HTTPException(status_code=400, detail="Invalid video format. Only mp4 allowed.")

    if audio_file.content_type not in {"audio/wav", "audio/x-wav", "audio/mpeg"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid audio format. Only wav or mp3 allowed.",
        )

    task_id = str(uuid.uuid4())

    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    video_path = task_dir / "input.mp4"
    audio_path = task_dir / "input_audio"

    # Preserve audio extension if available
    extension = Path(audio_file.filename or "").suffix or (
        ".mp3" if audio_file.content_type == "audio/mpeg" else ".wav"
    )
    audio_path = audio_path.with_suffix(extension)

    await _save_upload(video_file, video_path)
    await _save_upload(audio_file, audio_path)

    # Schedule background processing
    background_tasks.add_task(LipSyncService.process_task, task_id, video_path, audio_path, model_choice)

    return JSONResponse(status_code=202, content=ProcessResponse(task_id=task_id).model_dump())


@router.get("/result/{task_id}")
async def get_result(task_id: str):
    """Retrieve processing result for a given task ID.

    - If processing is ongoing, returns a status JSON.
    - If finished, streams the resulting mp4 file.
    """
    status = LipSyncService.get_status(task_id)
    if status != "finished":
        return ResultStatusResponse(status=status)

    result_path = LipSyncService.get_result_path(task_id)
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found.")

    # Stream the file
    return FileResponse(
        path=result_path,
        media_type="video/mp4",
        filename=f"{task_id}_lipsynced.mp4",
    )
