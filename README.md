# ModelLab Backend

FastAPI backend for lip-syncing videos with target audio. This version uses a mocked background service and is structured for easy future integration of real ML models.

## Features
- POST /process/ — upload video (mp4), audio (wav/mp3), and a model choice (model1|model2|model3); returns task_id
- GET /process/result/{task_id} — poll status or download resulting mp4 when finished
- Async file saves to /tmp/uploads
- BackgroundTasks simulate processing
- CORS enabled for all origins (adjust for production)

## Run locally
Use the provided virtual environment and start the server.

```bash
# Activate the venv if not already active
# (VS Code should auto-use .venv; otherwise on Windows Git Bash)
source .venv/Scripts/activate

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project structure
```
app/
  main.py
  routes/
    processing.py
  schemas/
    processing.py
  services/
    lipsync.py
```

## Notes
- Uploads and results are saved under /tmp/uploads. Ensure the runtime has permission to write there.
- Replace the mock service in `app/services/lipsync.py` with real model inference in the future.
