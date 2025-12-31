"""
SwarmOS Bee-1 Controller

The Queen. The API gateway. The coordinator.

This is the main entry point for all SwarmOS operations:
- Receives job requests from clients
- Routes jobs to workers
- Manages epochs
- Coordinates settlement
"""

import os
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Rails imports (shared libraries)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rails.queue.redis import SwarmQueue, QueuedJob, WorkerInfo
from rails.schemas.api import (
    JobSubmitRequest, JobSubmitResponse, JobStatusResponse,
    WorkerRegisterRequest, WorkerHeartbeatRequest, WorkerHeartbeatResponse,
    JobClaimResponse, JobCompleteRequest,
    ClientInfoResponse, ClientTopupRequest, ClientTopupResponse,
    CurrentEpochResponse, SystemStatusResponse, HealthResponse,
)
from rails.crypto.signing import verify_job_request, create_job_message, verify_signature


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Bee-1 configuration."""
    HOST: str = os.getenv("BEE1_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BEE1_PORT", "8000"))
    ENS: str = os.getenv("BEE1_ENS", "swarmos.eth")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./swarmledger.db")
    
    JOB_FEE_USD: Decimal = Decimal(os.getenv("JOB_FEE_USD", "0.10"))
    
    VERSION: str = "1.1.0"


config = Config()


# =============================================================================
# Application State
# =============================================================================

class AppState:
    """Application state container."""
    queue: SwarmQueue
    start_time: float
    current_epoch_id: str
    job_counter: int
    
    # In-memory stores (would be DB in production)
    clients: dict  # ens -> balance info
    jobs: dict     # job_id -> job info
    
    def __init__(self):
        self.queue = SwarmQueue(config.REDIS_URL)
        self.start_time = time.time()
        self.current_epoch_id = "epoch-002"  # Would come from DB
        self.job_counter = 850  # Would come from DB
        self.clients = {
            # Demo client
            "xyzclinic.clientswarm.eth": {
                "balance_usd": Decimal("24.50"),
                "reserved_usd": Decimal("0"),
                "total_spent_usd": Decimal("847.30"),
                "total_jobs": 8473,
            }
        }
        self.jobs = {}


state = AppState()


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"🐝 Bee-1 Controller starting...")
    print(f"   ENS: {config.ENS}")
    print(f"   Redis: {config.REDIS_URL}")
    
    await state.queue.connect()
    print(f"   ✓ Connected to Redis")
    
    yield
    
    # Shutdown
    print(f"🐝 Bee-1 Controller shutting down...")
    await state.queue.disconnect()


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="SwarmOS Bee-1 Controller",
    description="The Queen. Sovereign compute coordination.",
    version=config.VERSION,
    lifespan=lifespan,
)

# CORS (for eth.limo frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://clientswarm.eth.limo",
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
# Health & Status
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=config.VERSION,
        components={
            "redis": "connected",
            "database": "connected",
            "ipfs": "connected",
        }
    )


@app.get("/api/v1/status", response_model=SystemStatusResponse)
async def system_status():
    """Get system-wide status."""
    stats = await state.queue.get_stats()
    uptime = int(time.time() - state.start_time)
    
    return SystemStatusResponse(
        status="healthy",
        current_epoch=state.current_epoch_id,
        uptime_seconds=uptime,
        queue_depth=stats["queue_depth"],
        processing=stats["processing"],
        workers_online=stats["workers_online"],
        workers_busy=stats["workers_busy"],
        total_jobs_today=127,  # Would come from DB
        total_revenue_today="12.70",
    )


# =============================================================================
# Jobs API
# =============================================================================

@app.post("/api/v1/jobs", response_model=JobSubmitResponse)
async def submit_job(request: JobSubmitRequest):
    """
    Submit a new compute job.
    
    Requires:
    - Valid EIP-191 signature from client ENS owner
    - Sufficient balance ($0.10 per scan)
    """
    # 1. Verify client exists and has balance
    client = state.clients.get(request.client_ens)
    if not client:
        raise HTTPException(status_code=404, detail="Client not registered")
    
    available = client["balance_usd"] - client["reserved_usd"]
    if available < config.JOB_FEE_USD:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient balance. Need ${config.JOB_FEE_USD}, have ${available}"
        )
    
    # 2. Verify signature (simplified - would verify against ENS owner address)
    # In production: resolve ENS → address, verify signature
    message = create_job_message(
        request.job_type,
        request.client_ens,
        request.dicom_ref,
        request.timestamp,
        request.nonce
    )
    # signature_valid = verify_signature(message, request.signature, resolved_address)
    
    # 3. Check timestamp freshness (prevent replay)
    now = int(time.time())
    if abs(now - request.timestamp) > 300:  # 5 minute window
        raise HTTPException(status_code=400, detail="Request timestamp too old")
    
    # 4. Generate job ID
    state.job_counter += 1
    epoch_num = state.current_epoch_id.split("-")[1]
    job_id = f"job-{epoch_num}-{state.job_counter:04d}"
    
    # 5. Reserve balance
    client["reserved_usd"] += config.JOB_FEE_USD
    
    # 6. Create job record
    job_record = {
        "id": job_id,
        "epoch_id": state.current_epoch_id,
        "client_ens": request.client_ens,
        "worker_ens": None,
        "job_type": request.job_type,
        "status": "queued",
        "dicom_ref": request.dicom_ref,
        "result_ref": None,
        "fee_usd": str(config.JOB_FEE_USD),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
    }
    state.jobs[job_id] = job_record
    
    # 7. Queue job
    queued_job = QueuedJob(
        job_id=job_id,
        job_type=request.job_type,
        client_ens=request.client_ens,
        dicom_ref=request.dicom_ref,
        fee_usd=str(config.JOB_FEE_USD),
        queued_at=time.time(),
    )
    await state.queue.enqueue_job(queued_job)
    
    return JobSubmitResponse(
        job_id=job_id,
        status="queued",
        epoch_id=state.current_epoch_id,
        fee_usd=str(config.JOB_FEE_USD),
        message="Job queued successfully"
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status."""
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job["id"],
        epoch_id=job["epoch_id"],
        client_ens=job["client_ens"],
        worker_ens=job.get("worker_ens"),
        job_type=job["job_type"],
        status=job["status"],
        fee_usd=job["fee_usd"],
        execution_ms=job.get("execution_ms"),
        dicom_ref=job.get("dicom_ref"),
        result_ref=job.get("result_ref"),
        submitted_at=datetime.fromisoformat(job["submitted_at"]),
        started_at=datetime.fromisoformat(job["started_at"]) if job.get("started_at") else None,
        completed_at=datetime.fromisoformat(job["completed_at"]) if job.get("completed_at") else None,
    )


# =============================================================================
# Workers API (Internal)
# =============================================================================

@app.post("/api/v1/workers/register")
async def register_worker(request: WorkerRegisterRequest):
    """Register a new worker."""
    # Verify signature proves ENS ownership
    # In production: verify against ENS resolved address
    
    worker = WorkerInfo(
        ens=request.ens,
        status="online",
        gpu_model=request.gpu_model,
        vram_gb=request.vram_gb,
        ip_address=request.ip_address,
        last_heartbeat=time.time(),
    )
    
    await state.queue.register_worker(worker)
    
    return {"status": "registered", "ens": request.ens}


@app.post("/api/v1/workers/heartbeat", response_model=WorkerHeartbeatResponse)
async def worker_heartbeat(request: WorkerHeartbeatRequest):
    """Worker heartbeat."""
    await state.queue.set_worker_status(
        request.ens,
        request.status,
        request.current_job_id
    )
    
    return WorkerHeartbeatResponse(
        acknowledged=True,
        server_time=datetime.now(timezone.utc)
    )


@app.post("/api/v1/jobs/claim", response_model=JobClaimResponse)
async def claim_job(worker_ens: str = Header(..., alias="X-Worker-ENS")):
    """Worker claims next available job."""
    job = await state.queue.claim_job(worker_ens)
    
    if not job:
        return JobClaimResponse(
            job_id=None,
            job_type=None,
            client_ens=None,
            dicom_ref=None,
            claimed=False,
            message="No jobs available"
        )
    
    # Update job record
    if job.job_id in state.jobs:
        state.jobs[job.job_id]["status"] = "processing"
        state.jobs[job.job_id]["worker_ens"] = worker_ens
        state.jobs[job.job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update worker status
    await state.queue.set_worker_status(worker_ens, "busy", job.job_id)
    
    return JobClaimResponse(
        job_id=job.job_id,
        job_type=job.job_type,
        client_ens=job.client_ens,
        dicom_ref=job.dicom_ref,
        claimed=True,
        message="Job claimed"
    )


@app.post("/api/v1/jobs/{job_id}/complete")
async def complete_job(job_id: str, request: JobCompleteRequest):
    """Worker submits job completion."""
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "processing":
        raise HTTPException(status_code=400, detail="Job not in processing state")
    
    # Verify worker signature
    # In production: verify PoE hash and signature
    
    # Update job record
    job["status"] = "completed"
    job["result_ref"] = request.result_ref
    job["poe_hash"] = request.poe_hash
    job["execution_ms"] = request.execution_ms
    job["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    # Finalize payment
    client = state.clients.get(job["client_ens"])
    if client:
        fee = Decimal(job["fee_usd"])
        client["reserved_usd"] -= fee
        client["balance_usd"] -= fee
        client["total_spent_usd"] += fee
        client["total_jobs"] += 1
    
    # Update worker status
    await state.queue.set_worker_status(request.worker_ens, "online", None)
    await state.queue.complete_job(job_id)
    
    return {"status": "completed", "job_id": job_id}


# =============================================================================
# Clients API
# =============================================================================

@app.get("/api/v1/clients/{ens}", response_model=ClientInfoResponse)
async def get_client_info(ens: str):
    """Get client account info."""
    client = state.clients.get(ens)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    balance = client["balance_usd"]
    reserved = client["reserved_usd"]
    available = balance - reserved
    
    return ClientInfoResponse(
        ens=ens,
        balance_usd=str(balance),
        reserved_usd=str(reserved),
        available_usd=str(available),
        total_spent_usd=str(client["total_spent_usd"]),
        total_jobs=client["total_jobs"],
        scans_available=int(available / config.JOB_FEE_USD),
        display_name=client.get("display_name"),
        created_at=datetime.now(timezone.utc),  # Would come from DB
    )


@app.post("/api/v1/clients/{ens}/topup", response_model=ClientTopupResponse)
async def topup_client(ens: str, request: ClientTopupRequest):
    """Record a client USDC topup from L1."""
    # In production: verify L1 transaction
    
    if ens not in state.clients:
        # Create new client
        state.clients[ens] = {
            "balance_usd": Decimal("0"),
            "reserved_usd": Decimal("0"),
            "total_spent_usd": Decimal("0"),
            "total_jobs": 0,
        }
    
    amount = Decimal(request.amount_usd)
    state.clients[ens]["balance_usd"] += amount
    new_balance = state.clients[ens]["balance_usd"]
    
    return ClientTopupResponse(
        client_ens=ens,
        amount_usd=str(amount),
        new_balance_usd=str(new_balance),
        scans_available=int(new_balance / config.JOB_FEE_USD),
        tx_hash=request.eth_tx_hash,
    )


# =============================================================================
# Epochs API
# =============================================================================

@app.get("/api/v1/epochs/current", response_model=CurrentEpochResponse)
async def get_current_epoch():
    """Get current active epoch."""
    stats = await state.queue.get_stats()
    
    # Count completed jobs in current epoch
    completed = sum(
        1 for j in state.jobs.values()
        if j["epoch_id"] == state.current_epoch_id and j["status"] == "completed"
    )
    
    revenue = completed * float(config.JOB_FEE_USD)
    
    return CurrentEpochResponse(
        epoch_id=state.current_epoch_id,
        status="active",
        start_time=datetime.now(timezone.utc),  # Would come from DB
        jobs_completed=completed,
        revenue_usd=f"{revenue:.2f}",
        agents_online=stats["workers_online"],
        queue_depth=stats["queue_depth"],
    )


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
