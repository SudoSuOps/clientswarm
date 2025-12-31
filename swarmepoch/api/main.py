"""
SwarmEpoch API

The Immutable Archive for SwarmOS.

Provides:
- Epoch listing and details
- Job receipts with Merkle proofs
- Verification endpoints
- IPFS hash lookups
"""

import os
import hashlib
import json
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
    HOST: str = os.getenv("SWARMEPOCH_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SWARMEPOCH_PORT", "8300"))
    ENS: str = "swarmepoch.eth"
    VERSION: str = "1.0.0"


config = Config()


# =============================================================================
# Schemas
# =============================================================================

class EpochSummary(BaseModel):
    epoch_id: str
    status: str  # active, sealing, finalized
    jobs_count: int
    total_revenue_usd: str
    jobs_merkle_root: str | None
    agents_count: int
    clients_count: int
    start_time: str
    sealed_at: str | None
    ipfs_hash: str | None


class JobReceipt(BaseModel):
    receipt_version: str
    job_id: str
    epoch_id: str
    client: str
    agent: str
    job_type: str
    price: str
    currency: str
    timing: dict
    leaf_hash: str
    jobs_merkle_root: str
    merkle_proof: list[dict]
    epoch_signature_ref: str


class VerifyRequest(BaseModel):
    job_id: str
    epoch_id: str
    leaf_hash: str
    merkle_proof: list[dict]


# =============================================================================
# Demo Data
# =============================================================================

class EpochStore:
    def __init__(self):
        self.epochs = {
            "epoch-000": {
                "epoch_id": "epoch-000",
                "status": "finalized",
                "jobs_count": 0,
                "total_revenue_usd": "0.00",
                "jobs_merkle_root": "0000000000000000000000000000000000000000000000000000000000000000",
                "agents_count": 0,
                "clients_count": 0,
                "start_time": "2025-01-01T00:00:00Z",
                "sealed_at": "2025-01-01T00:00:00Z",
                "ipfs_hash": "QmGenesisEpochHash",
            },
            "epoch-001": {
                "epoch_id": "epoch-001",
                "status": "finalized",
                "jobs_count": 105,
                "total_revenue_usd": "10.50",
                "jobs_merkle_root": "7ec20e03b05b7898c3cdc33f0d066ddf860091338eaace5ad51df1f1f8c472b5",
                "agents_count": 3,
                "clients_count": 8,
                "start_time": "2025-01-15T00:00:00Z",
                "sealed_at": "2025-01-16T00:00:00Z",
                "ipfs_hash": "QmEpoch001HashXYZ",
                "treasury": {
                    "total_revenue_usd": "10.50",
                    "work_pool_usd": "6.85",
                    "readiness_pool_usd": "2.94",
                    "protocol_fee_usd": "0.21",
                    "operator_fee_usd": "0.53",
                },
            },
            "epoch-002": {
                "epoch_id": "epoch-002",
                "status": "finalized",
                "jobs_count": 248,
                "total_revenue_usd": "24.80",
                "jobs_merkle_root": "a3f891c2e7d4b5f6a8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
                "agents_count": 5,
                "clients_count": 12,
                "start_time": "2025-01-16T00:00:00Z",
                "sealed_at": "2025-01-17T00:00:00Z",
                "ipfs_hash": "QmEpoch002HashABC",
                "treasury": {
                    "total_revenue_usd": "24.80",
                    "work_pool_usd": "16.18",
                    "readiness_pool_usd": "6.94",
                    "protocol_fee_usd": "0.50",
                    "operator_fee_usd": "1.24",
                },
            },
            "epoch-003": {
                "epoch_id": "epoch-003",
                "status": "active",
                "jobs_count": 67,
                "total_revenue_usd": "6.70",
                "jobs_merkle_root": None,
                "agents_count": 5,
                "clients_count": 9,
                "start_time": "2025-01-17T00:00:00Z",
                "sealed_at": None,
                "ipfs_hash": None,
            },
        }
        
        # Sample jobs for receipts
        self.jobs = {
            "job-002-0001": {
                "id": "job-002-0001",
                "epoch_id": "epoch-002",
                "client": "xyz.clientswarm.eth",
                "agent": "bee-01.swarmbee.eth",
                "type": "spine_mri",
                "fee_usd": "0.10",
                "execution_ms": 2847,
                "poe_hash": "7ec20e03b05b7898c3cdc33f0d066ddf",
                "submitted_at": "2025-01-16T08:23:45Z",
                "completed_at": "2025-01-16T08:23:48Z",
            },
            "job-002-0042": {
                "id": "job-002-0042",
                "epoch_id": "epoch-002",
                "client": "acme.clientswarm.eth",
                "agent": "bee-02.swarmbee.eth",
                "type": "brain_mri",
                "fee_usd": "0.10",
                "execution_ms": 3102,
                "poe_hash": "a3f891c2e7d4b5f6a8c9d0e1f2a3b4c5",
                "submitted_at": "2025-01-16T14:17:22Z",
                "completed_at": "2025-01-16T14:17:25Z",
            },
        }
        
        # Sample agents
        self.agents = {
            "epoch-002": [
                {
                    "ens": "bee-01.swarmbee.eth",
                    "jobs_completed": 87,
                    "uptime_seconds": 86400,
                    "poe_success_rate": 1.0,
                    "work_share_usd": "5.66",
                    "readiness_share_usd": "1.39",
                    "total_payout_usd": "7.05",
                },
                {
                    "ens": "bee-02.swarmbee.eth",
                    "jobs_completed": 64,
                    "uptime_seconds": 86400,
                    "poe_success_rate": 1.0,
                    "work_share_usd": "4.16",
                    "readiness_share_usd": "1.39",
                    "total_payout_usd": "5.55",
                },
                {
                    "ens": "bee-03.swarmbee.eth",
                    "jobs_completed": 52,
                    "uptime_seconds": 86400,
                    "poe_success_rate": 1.0,
                    "work_share_usd": "3.38",
                    "readiness_share_usd": "1.39",
                    "total_payout_usd": "4.77",
                },
                {
                    "ens": "bee-04.swarmbee.eth",
                    "jobs_completed": 28,
                    "uptime_seconds": 86400,
                    "poe_success_rate": 1.0,
                    "work_share_usd": "1.82",
                    "readiness_share_usd": "1.39",
                    "total_payout_usd": "3.21",
                },
                {
                    "ens": "bee-05.swarmbee.eth",
                    "jobs_completed": 17,
                    "uptime_seconds": 86400,
                    "poe_success_rate": 1.0,
                    "work_share_usd": "1.11",
                    "readiness_share_usd": "1.39",
                    "total_payout_usd": "2.50",
                },
            ]
        }
    
    def get_all_epochs(self) -> list[dict]:
        return sorted(
            self.epochs.values(),
            key=lambda e: e["epoch_id"],
            reverse=True
        )
    
    def get_epoch(self, epoch_id: str) -> dict | None:
        return self.epochs.get(epoch_id)
    
    def get_current_epoch(self) -> dict | None:
        for epoch in self.epochs.values():
            if epoch["status"] == "active":
                return epoch
        return None
    
    def get_job(self, job_id: str) -> dict | None:
        return self.jobs.get(job_id)
    
    def get_agents(self, epoch_id: str) -> list[dict]:
        return self.agents.get(epoch_id, [])
    
    def generate_receipt(self, job: dict) -> dict:
        """Generate a receipt with mock Merkle proof."""
        epoch = self.epochs.get(job["epoch_id"])
        if not epoch or not epoch.get("jobs_merkle_root"):
            return None
        
        # Mock leaf hash
        leaf_data = json.dumps(job, sort_keys=True).encode()
        leaf_hash = hashlib.sha256(leaf_data).hexdigest()
        
        # Mock Merkle proof (in reality would be computed)
        mock_proof = [
            {"hash": "b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5", "position": "right"},
            {"hash": "c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6", "position": "left"},
            {"hash": "d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7", "position": "right"},
        ]
        
        return {
            "receipt_version": "1.1.0",
            "job_id": job["id"],
            "epoch_id": job["epoch_id"],
            "client": job["client"],
            "agent": job["agent"],
            "job_type": job["type"],
            "price": job["fee_usd"],
            "currency": "USD",
            "timing": {
                "submitted_utc": job["submitted_at"],
                "completed_utc": job["completed_at"],
            },
            "leaf_hash": leaf_hash,
            "jobs_merkle_root": epoch["jobs_merkle_root"],
            "merkle_proof": mock_proof,
            "epoch_signature_ref": f"ipfs://{epoch.get('ipfs_hash', 'pending')}/SIGNATURE.txt",
        }


store = EpochStore()


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"📦 SwarmEpoch API starting...")
    print(f"   ENS: {config.ENS}")
    yield
    print(f"📦 SwarmEpoch API shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="SwarmEpoch API",
    description="Immutable archive for SwarmOS epochs",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://swarmepoch.eth.limo",
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
        "service": "swarmepoch",
        "version": config.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/stats")
async def get_stats():
    """Get archive-wide statistics."""
    epochs = store.get_all_epochs()
    finalized = [e for e in epochs if e["status"] == "finalized"]
    
    total_jobs = sum(e["jobs_count"] for e in finalized)
    total_revenue = sum(float(e["total_revenue_usd"]) for e in finalized)
    
    return {
        "epochs_total": len(epochs),
        "epochs_finalized": len(finalized),
        "total_jobs_archived": total_jobs,
        "total_revenue_settled_usd": f"{total_revenue:.2f}",
        "latest_epoch": epochs[0]["epoch_id"] if epochs else None,
    }


@app.get("/v1/epochs")
async def list_epochs():
    """List all epochs."""
    epochs = store.get_all_epochs()
    return {
        "epochs": epochs,
        "total": len(epochs),
    }


@app.get("/v1/epochs/current")
async def get_current_epoch():
    """Get current active epoch."""
    epoch = store.get_current_epoch()
    if not epoch:
        raise HTTPException(status_code=404, detail="No active epoch")
    return epoch


@app.get("/v1/epochs/{epoch_id}")
async def get_epoch(epoch_id: str):
    """Get epoch details."""
    epoch = store.get_epoch(epoch_id)
    if not epoch:
        raise HTTPException(status_code=404, detail="Epoch not found")
    return epoch


@app.get("/v1/epochs/{epoch_id}/agents")
async def get_epoch_agents(epoch_id: str):
    """Get agent stats for an epoch."""
    epoch = store.get_epoch(epoch_id)
    if not epoch:
        raise HTTPException(status_code=404, detail="Epoch not found")
    
    agents = store.get_agents(epoch_id)
    return {
        "epoch_id": epoch_id,
        "agents": agents,
        "total": len(agents),
    }


@app.get("/v1/epochs/{epoch_id}/ipfs")
async def get_epoch_ipfs(epoch_id: str):
    """Get IPFS hash for epoch bundle."""
    epoch = store.get_epoch(epoch_id)
    if not epoch:
        raise HTTPException(status_code=404, detail="Epoch not found")
    
    if not epoch.get("ipfs_hash"):
        raise HTTPException(status_code=404, detail="Epoch not yet sealed")
    
    return {
        "epoch_id": epoch_id,
        "ipfs_hash": epoch["ipfs_hash"],
        "gateway_url": f"https://ipfs.io/ipfs/{epoch['ipfs_hash']}/",
        "files": [
            "SUMMARY.json",
            "jobs.json",
            "agents.json",
            "SIGNATURE.txt",
        ],
    }


@app.get("/v1/jobs/{job_id}/receipt", response_model=JobReceipt)
async def get_job_receipt(job_id: str):
    """Get job receipt with Merkle proof."""
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    receipt = store.generate_receipt(job)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not available (epoch not sealed)")
    
    return receipt


@app.post("/v1/verify")
async def verify_receipt(request: VerifyRequest):
    """Verify a job receipt against epoch Merkle root."""
    epoch = store.get_epoch(request.epoch_id)
    if not epoch:
        return {"valid": False, "error": "Epoch not found"}
    
    if not epoch.get("jobs_merkle_root"):
        return {"valid": False, "error": "Epoch not sealed"}
    
    # In production: actually verify the Merkle proof
    # For demo: simulate verification
    
    return {
        "valid": True,
        "job_id": request.job_id,
        "epoch_id": request.epoch_id,
        "epoch_merkle_root": epoch["jobs_merkle_root"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/index")
async def get_index():
    """Get epoch index (for SwarmOrb)."""
    epochs = store.get_all_epochs()
    finalized = [e for e in epochs if e["status"] == "finalized" and e.get("ipfs_hash")]
    
    return {
        "version": "1.1.0",
        "latest_epoch": epochs[0]["epoch_id"] if epochs else None,
        "current_epoch": store.get_current_epoch()["epoch_id"] if store.get_current_epoch() else None,
        "epochs": {
            e["epoch_id"]: f"ipfs://{e['ipfs_hash']}/"
            for e in finalized
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
