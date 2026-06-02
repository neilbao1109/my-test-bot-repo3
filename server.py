import uuid
import time
import threading
import subprocess
import base64
import os
from queue import Queue
from typing import Optional, Dict, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config

app = FastAPI(title="mflux Local Image Generation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(config.OUTPUT_DIR, exist_ok=True)

# --- Models ---

class GenerateRequest(BaseModel):
    prompt: str
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None
    seed: Optional[int] = None
    model: Optional[str] = None
    quantize: Optional[int] = None  # -q flag: 4 or 8
    response_format: Optional[str] = "url"  # "url" or "b64_json"

class TaskInfo:
    def __init__(self, task_id: str, req: GenerateRequest):
        self.task_id = task_id
        self.status = "queued"  # queued / generating / completed / failed
        self.request = req
        self.filename: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow().isoformat()
        self.completed_at: Optional[str] = None

# --- State ---

tasks: Dict[str, TaskInfo] = {}
history: List[dict] = []
task_queue: Queue = Queue()
current_task_id: Optional[str] = None
lock = threading.Lock()

# --- Worker ---

def worker():
    global current_task_id
    while True:
        task_id = task_queue.get()
        task = tasks.get(task_id)
        if not task:
            task_queue.task_done()
            continue

        with lock:
            task.status = "generating"
            current_task_id = task_id

        req = task.request
        width = req.width or config.DEFAULT_WIDTH
        height = req.height or config.DEFAULT_HEIGHT
        steps = req.steps or config.DEFAULT_STEPS
        model = req.model or config.DEFAULT_MODEL
        seed = req.seed

        short_id = task_id[:8]
        timestamp = int(time.time())
        filename = f"{timestamp}_{short_id}.png"
        output_path = os.path.join(config.OUTPUT_DIR, filename)

        quantize = req.quantize or config.DEFAULT_QUANTIZE

        cmd = [
            "mflux-generate-flux2",
            "--prompt", req.prompt,
            "--width", str(width),
            "--height", str(height),
            "--steps", str(steps),
            "--model", model,
            "-q", str(quantize),
            "-o", output_path,
        ]
        if seed is not None:
            cmd.extend(["--seed", str(seed)])

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            task.status = "completed"
            task.filename = filename
            task.completed_at = datetime.utcnow().isoformat()
            history.append({
                "task_id": task_id,
                "prompt": req.prompt,
                "params": {"width": width, "height": height, "steps": steps, "seed": seed, "model": model, "quantize": quantize},
                "filename": filename,
                "created_at": task.created_at,
            })
            if len(history) > 20:
                history.pop(0)
        except subprocess.CalledProcessError as e:
            task.status = "failed"
            task.error = e.stderr or str(e)
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
        finally:
            with lock:
                current_task_id = None
            task_queue.task_done()

worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()

# --- Routes ---

@app.post("/generate")
def generate(req: GenerateRequest):
    task_id = str(uuid.uuid4())
    task = TaskInfo(task_id, req)
    tasks[task_id] = task
    task_queue.put(task_id)
    return {"task_id": task_id, "status": "queued"}

@app.get("/task/{task_id}")
def get_task(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    result = {"task_id": task_id, "status": task.status}
    if task.status == "completed":
        result["image_url"] = f"/images/{task.filename}"
        if task.request.response_format == "b64_json":
            filepath = os.path.join(config.OUTPUT_DIR, task.filename)
            with open(filepath, "rb") as f:
                result["b64_json"] = base64.b64encode(f.read()).decode()
    elif task.status == "failed":
        result["error"] = task.error
    return result

@app.get("/status")
def get_status():
    with lock:
        if current_task_id:
            task = tasks.get(current_task_id)
            return {
                "status": "generating",
                "current_task": {
                    "task_id": current_task_id,
                    "prompt": task.request.prompt if task else None,
                },
                "queued": task_queue.qsize(),
            }
        return {"status": "idle", "queued": task_queue.qsize()}

@app.get("/images/{filename}")
def get_image(filename: str):
    filepath = os.path.join(config.OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath, media_type="image/png")

@app.get("/history")
def get_history():
    return list(reversed(history))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
