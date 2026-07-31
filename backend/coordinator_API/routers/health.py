"""
routers/health.py - GET /, GET /health, GET /api/metrics/system,
GET /api/logs/stream, GET /dashboard, GET /dashboard-login.

Also carries get_gpu_metrics()/get_system_metrics() (dead helpers - shadowed
by/unrelated to the real @router.get("/api/metrics/system") handler below,
relocated as-is) and the GPU_AVAILABLE dead flag, per the approved cleanup
plan.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from coordinator_API.core.config import APP_DIR
from coordinator_API.core.security import require_admin_secret
import coordinator_API.core.state as state

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️ GPUtil not installed. Install with: pip install gputil")

router = APIRouter()


# ==================== SYSTEM METRICS HELPERS (V2 Enhanced) - DEAD CODE ====================
# Shadowed by the real @router.get("/api/metrics/system") handler below;
# neither is called by name anywhere. Relocated as-is.

def get_gpu_metrics():
    """Get GPU metrics using GPUtil or safe fallback"""
    import torch
    if not torch.cuda.is_available():
        import random
        return {
            "gpu_utilization": random.uniform(5, 15), # Simulated idle
            "gpu_memory_used": 0,
            "gpu_memory_total": 0,
            "gpu_temperature": 35.0,
        }

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if not gpus: return {"gpu_utilization": 0, "gpu_memory_used": 0, "gpu_memory_total": 0, "gpu_temperature": 0}

        gpu = gpus[0]
        return {
            "gpu_utilization": gpu.load * 100,
            "gpu_memory_used": gpu.memoryUsed / 1024,
            "gpu_memory_total": gpu.memoryTotal / 1024,
            "gpu_temperature": gpu.temperature,
        }
    except:
        return {"gpu_utilization": 45.0, "gpu_memory_used": 2.1, "gpu_memory_total": 8.0, "gpu_temperature": 55.0}

def get_system_metrics():
    """Get CPU and memory metrics"""
    import psutil
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        return {
            "cpu_utilization": cpu_percent,
            "system_memory_used": mem.used / (1024**3),
            "system_memory_total": mem.total / (1024**3),
        }
    except Exception:
        return {"cpu_utilization": 15.0, "system_memory_used": 4.5, "system_memory_total": 16.0}


@router.get("/")
async def root():
    return {
        "service": "AICP Coordinator",
        "version": "5.0.0",
        "features": ["Real Duke ML", "Trust Scoring", "Semantic Matching"],
        "dashboard": "http://localhost:3000/dashboard"
    }

@router.get("/health")
async def health():
    return {"status": "ok", "service": "AICP Coordinator"}


@router.get("/api/metrics/system")
async def get_system_metrics_route():
    """Get real-time system performance metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory metrics
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)

        # GPU metrics
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Get first GPU
                gpu_utilization = gpu.load * 100
                gpu_memory_used = gpu.memoryUsed / 1024  # Convert to GB
                gpu_memory_total = gpu.memoryTotal / 1024
                gpu_temperature = gpu.temperature
            else:
                gpu_utilization = 0
                gpu_memory_used = 0
                gpu_memory_total = 0
                gpu_temperature = 0
        except:
            gpu_utilization = 0
            gpu_memory_used = 0
            gpu_memory_total = 8.55  # Default from logs
            gpu_temperature = 0

        metrics = {
            "cpu_utilization": cpu_percent,
            "system_memory_used": memory_used_gb,
            "system_memory_total": memory_total_gb,
            "gpu_utilization": gpu_utilization,
            "gpu_memory_used": gpu_memory_used,
            "gpu_memory_total": gpu_memory_total,
            "gpu_temperature": gpu_temperature,
            "requests_per_sec": len(state.active_connections) * 0.5,  # Simulated
            "timestamp": datetime.now().isoformat()
        }

        # Log metrics periodically
        if int(datetime.now().timestamp()) % 30 == 0:  # Every 30 seconds
            state.write_log(f"INFO: GPU: {gpu_utilization:.1f}% | RAM: {memory_used_gb:.1f}GB | CPU: {cpu_percent:.1f}%")

        return metrics

    except Exception as e:
        state.write_log(f"ERROR: Failed to fetch system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get("/api/logs/stream", dependencies=[Depends(require_admin_secret)])
async def stream_logs(request: Request):
    """Server-Sent Events endpoint for real-time logs"""

    async def log_generator():
        connection_id = id(asyncio.current_task())
        state.active_connections.add(connection_id)

        # Send initial connection message
        yield f"data: [SYSTEM] Neural stream connected (ID: {connection_id})\n\n"
        state.write_log(f"INFO: Client {connection_id} connected to Neural Stream")

        try:
            # Open log file and seek to end
            with open(state.LOG_FILE, "r") as f:
                f.seek(0, 2)  # Go to end of file

                while True:
                    # CRITICAL: Check if client is still connected
                    if await request.is_disconnected():
                       # Silent disconnected - this is normal, don't log it
                        pass

                    # Read new lines
                    line = f.readline()
                    if not line:
                        # No new data, send heartbeat and wait
                        yield ": heartbeat\n\n"
                        await asyncio.sleep(1.0)
                        continue

                    # Send the log line
                    yield f"data: {line.strip()}\n\n"

        except asyncio.CancelledError:
            # Client disconnected - this is normal, don't log it
            pass
        except Exception as e:
            state.write_log(f"ERROR: Stream error for client {connection_id}: {str(e)}")
            print(f"❌ Stream error: {e}")
        finally:
            # Cleanup
            state.active_connections.discard(connection_id)

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ----------------- DASHBOARD -----------------
@router.get("/dashboard")
async def get_dashboard():
    """Redirect to React frontend on port 3000"""
    return RedirectResponse(url="http://localhost:3000/dashboard", status_code=307)

# NOTE: the old public, unauthenticated "/admin" HTML control panel (plain
# buttons that POSTed straight to /admin/clear-cache and /admin/retrain-agents
# with no auth at all) has been removed. Admin operations now live behind
# the real admin portal at labeele.ai/admin (Supabase-gated) and this API's
# own require_admin_secret dependency - a bare HTML page pointed at this
# backend can no longer trigger anything.

@router.get("/dashboard-login", response_class=HTMLResponse)
async def get_dashboard_login():
    """New dashboard with JWT authentication"""
    # APP_DIR fix: was Path(__file__).parent, which assumed __file__ was
    # coordinator_api.py's own location.
    dashboard_file = Path(APP_DIR) / "dashboard-login.html"

    if dashboard_file.exists():
        with open(dashboard_file, 'r') as f:
            html = f.read()
        return HTMLResponse(content=html)
    else:
        return HTMLResponse(content="<h1>❌ dashboard-login.html not found</h1>")
