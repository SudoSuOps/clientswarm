"""
SwarmBee API

Worker Registry for SwarmOS.

Provides:
- Worker registration
- Status endpoints
- Hardware inventory
- Leaderboard
"""

import os
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =============================================================================
# Configuration
# =============================================================================

class Config:
    HOST: str = os.getenv("SWARMBEE_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SWARMBEE_PORT", "8200"))
    ENS: str = "swarmbee.eth"
    VERSION: str = "1.0.0"


config = Config()


# =============================================================================
# Schemas
# =============================================================================

class WorkerInfo(BaseModel):
    ens: str
    role: str
    status: str  # online, busy, offline, draining
    gpu_model: str
    gpu_count: int
    vram_gb: int
    cuda_version: str
    jobs_completed: int
    total_earned_usd: str
    uptime_pct: float
    current_job: str | None = None
    last_heartbeat: str


class SwarmStats(BaseModel):
    total_gpus: int
    total_vram_tb: float
    active_workers: int
    busy_workers: int
    total_jobs: int
    avg_uptime_pct: float


class HardwareInventory(BaseModel):
    gpu_model: str
    count: int
    vram_per_gpu_gb: int
    total_vram_gb: int


# =============================================================================
# In-Memory Store
# =============================================================================

class WorkerStore:
    def __init__(self):
        self.workers = {
            "bee-01.swarmbee.eth": {
                "ens": "bee-01.swarmbee.eth",
                "role": "Primary Worker",
                "status": "online",
                "gpu_model": "RTX 5090",
                "gpu_count": 8,
                "vram_gb": 256,
                "cuda_version": "12.4",
                "jobs_completed": 2847,
                "total_earned_usd": "847.30",
                "uptime_pct": 99.9,
                "current_job": None,
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            },
            "bee-02.swarmbee.eth": {
                "ens": "bee-02.swarmbee.eth",
                "role": "Inference Node",
                "status": "busy",
                "gpu_model": "RTX 6000 Ada",
                "gpu_count": 8,
                "vram_gb": 384,
                "cuda_version": "12.4",
                "jobs_completed": 2134,
                "total_earned_usd": "623.15",
                "uptime_pct": 99.8,
                "current_job": "job-003-0069",
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            },
            "bee-03.swarmbee.eth": {
                "ens": "bee-03.swarmbee.eth",
                "role": "Batch Processor",
                "status": "online",
                "gpu_model": "RTX 3090",
                "gpu_count": 8,
                "vram_gb": 192,
                "cuda_version": "12.2",
                "jobs_completed": 1892,
                "total_earned_usd": "412.80",
                "uptime_pct": 99.5,
                "current_job": None,
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            },
            "bee-04.swarmbee.eth": {
                "ens": "bee-04.swarmbee.eth",
                "role": "Training Node",
                "status": "online",
                "gpu_model": "RTX 5090",
                "gpu_count": 8,
                "vram_gb": 256,
                "cuda_version": "12.4",
                "jobs_completed": 892,
                "total_earned_usd": "198.40",
                "uptime_pct": 99.7,
                "current_job": None,
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            },
            "bee-05.swarmbee.eth": {
                "ens": "bee-05.swarmbee.eth",
                "role": "Medical AI",
                "status": "busy",
                "gpu_model": "RTX 6000 Ada",
                "gpu_count": 8,
                "vram_gb": 384,
                "cuda_version": "12.4",
                "jobs_completed": 708,
                "total_earned_usd": "156.20",
                "uptime_pct": 99.6,
                "current_job": "job-003-0070",
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            },
        }
        
        self.hardware_inventory = [
            {"gpu_model": "RTX 5090", "count": 48, "vram_per_gpu_gb": 32},
            {"gpu_model": "RTX 6000 Ada", "count": 48, "vram_per_gpu_gb": 48},
            {"gpu_model": "RTX 3090", "count": 200, "vram_per_gpu_gb": 24},
        ]
    
    def get_all_workers(self) -> list[dict]:
        return list(self.workers.values())
    
    def get_worker(self, ens: str) -> dict | None:
        return self.workers.get(ens)
    
    def get_online_workers(self) -> list[dict]:
        return [w for w in self.workers.values() if w["status"] in ("online", "busy")]
    
    def get_stats(self) -> dict:
        workers = list(self.workers.values())
        online = [w for w in workers if w["status"] in ("online", "busy")]
        busy = [w for w in workers if w["status"] == "busy"]
        
        total_gpus = sum(h["count"] for h in self.hardware_inventory)
        total_vram_tb = sum(h["count"] * h["vram_per_gpu_gb"] for h in self.hardware_inventory) / 1000
        total_jobs = sum(w["jobs_completed"] for w in workers)
        avg_uptime = sum(w["uptime_pct"] for w in workers) / len(workers) if workers else 0
        
        return {
            "total_gpus": total_gpus,
            "total_vram_tb": round(total_vram_tb, 1),
            "active_workers": len(online),
            "busy_workers": len(busy),
            "total_jobs": total_jobs,
            "avg_uptime_pct": round(avg_uptime, 1),
        }
    
    def get_hardware(self) -> list[dict]:
        return [
            {
                **h,
                "total_vram_gb": h["count"] * h["vram_per_gpu_gb"],
            }
            for h in self.hardware_inventory
        ]
    
    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        workers = list(self.workers.values())
        return sorted(workers, key=lambda w: w["jobs_completed"], reverse=True)[:limit]


store = WorkerStore()


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🐝 SwarmBee API starting...")
    print(f"   ENS: {config.ENS}")
    yield
    print(f"🐝 SwarmBee API shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="SwarmBee API",
    description="Worker registry for SwarmOS",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://swarmbee.eth.limo",
        "https://swarmorb.eth.limo",
        "https://swarmos.eth.limo",
        "http://localhost:3000",
        "http://localhost:4321",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "swarmbee",
        "version": config.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/stats", response_model=SwarmStats)
async def get_stats():
    """Get swarm-wide statistics."""
    return store.get_stats()


@app.get("/v1/workers")
async def list_workers(status: str | None = None):
    """List all workers, optionally filtered by status."""
    workers = store.get_all_workers()
    if status:
        workers = [w for w in workers if w["status"] == status]
    return {"workers": workers, "total": len(workers)}


@app.get("/v1/workers/{ens}", response_model=WorkerInfo)
async def get_worker(ens: str):
    """Get specific worker info."""
    worker = store.get_worker(ens)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@app.get("/v1/hardware")
async def get_hardware():
    """Get hardware inventory."""
    hardware = store.get_hardware()
    total_gpus = sum(h["count"] for h in hardware)
    total_vram_tb = sum(h["total_vram_gb"] for h in hardware) / 1000
    
    return {
        "inventory": hardware,
        "total_gpus": total_gpus,
        "total_vram_tb": round(total_vram_tb, 1),
    }


@app.get("/v1/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get top workers by jobs completed."""
    return {
        "leaderboard": store.get_leaderboard(limit),
        "metric": "jobs_completed",
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
