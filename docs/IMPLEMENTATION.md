# ModelLab Backend — Implementation Details

This document describes the architecture, routes, schemas, services, storage layout, and how to run and extend the backend.

## Overview
- Framework: FastAPI
- Runtime: Python 3.11
- ASGI server: Uvicorn (reload for dev)
- Async IO: `aiofiles` for streamed file writes
- Upload location: `/tmp/uploads/` (Linux-style temp path)
- Result location: `/tmp/uploads/results/`
- Background processing: FastAPI `BackgroundTasks`
- CORS: allowed for all origins (adjust in production)

## Project Structure
```
app/
  __init__.py
  main.py                  # FastAPI app + CORS + router include
  routes/
    __init__.py
    processing.py          # Endpoints for process & result
  schemas/
    __init__.py
    processing.py          # Pydantic models & enums
  services/
    __init__.py
    lipsync.py             # Mock async processing service
requirements.txt
README.md
```

## API
### POST /process/
- Form-data fields:
  - `video_file`: UploadFile (mp4); content_type must be `video/mp4`
  - `audio_file`: UploadFile (wav or mp3); content_type `audio/wav`, `audio/x-wav`, or `audio/mpeg`
  - `model_choice`: Enum `model1|model2|model3`
- Behavior:
  1. Validates file types and model choice (Pydantic enum enforces model).
  2. Saves files to `/tmp/uploads/<task_id>/input.mp4` and `/tmp/uploads/<task_id>/input_audio.<ext>` using async chunked writes.
  3. Schedules background task in `LipSyncService` to simulate processing and write a placeholder MP4 into `/tmp/uploads/results/<task_id>.mp4`.
- Response: `202 Accepted` with body: `{ "task_id": "<uuid>" }`
- Errors:
  - 400 on invalid file formats.
  - 422 if missing required form fields or invalid enum.

### GET /result/{task_id}
- Behavior:
  - If task not finished: returns `{ "status": "processing" }`.
  - If finished: returns a `FileResponse` streaming `video/mp4` named `<task_id>_lipsynced.mp4`.
- Errors:
  - 404 if a finished task has no result file present.

## Schemas (`app/schemas/processing.py`)
- `ModelChoice` (Enum): `model1`, `model2`, `model3`
- `ProcessResponse`: `{ task_id: str }`
- `ResultStatusResponse`: `{ status: str }` where values are `processing|finished`

## Service (`app/services/lipsync.py`)
- Maintains in-memory task registry: `{ task_id: TaskInfo }`
- `process_task` (async): simulates 2s delay, writes tiny placeholder MP4 bytes, updates task status to `finished`.
- `get_status(task_id)`: returns `processing` if unknown or not finished; `finished` when complete.
- `get_result_path(task_id)`: returns path to the expected result file.
- Notes:
  - The placeholder "mp4" is not a real playable video; it’s an IO stub. Replace with real pipeline later.
  - Add persistence (DB/Redis/object store) if you need durability across restarts.

## Error Handling
- Content-type validation for files with clear 400 messages.
- Pydantic enum automatically validates `model_choice`; FastAPI returns 422 on invalid.
- 404 for missing result files when status says finished.

## CORS
- Configured to allow any origin for development:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- Restrict in production (set specific origins).

## Storage Layout
```
/tmp/uploads/
  <task_id>/
    input.mp4
    input_audio.<ext>
  results/
    <task_id>.mp4
```

## Running Locally
- Ensure the venv is active and dependencies installed.
- Start the server with reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Extending to Real Models
- Replace `process_task` logic to:
  1. Decode inputs and run your lip-sync pipeline (e.g., Wav2Lip or other models).
  2. Stream outputs to a proper mp4 using ffmpeg or moviepy.
  3. Write the final artifact to `results/<task_id>.mp4`.
- Consider:
  - GPU/CPU device management and long-running workers
  - Job queue (RQ/Celery/Arq) for robust background execution
  - Persistent state (DB) for jobs and metadata
  - Signed URLs for result downloads

## Testing Ideas
- Unit tests for content-type validation and enum handling.
- Integration test: submit small files, poll result, expect 200 file stream after simulated delay.

## Security Considerations
- Restrict CORS in production to trusted domains.
- Validate file sizes and enforce limits.
- Store uploads in non-world-readable directories; clean up old tasks.
- Consider auth if exposing publicly.
