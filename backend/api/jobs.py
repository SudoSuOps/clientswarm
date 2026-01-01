"""
Jobs API - Submit and track inference jobs
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from api.auth import get_current_client
from services.database import get_jobs_collection, get_clients_collection
from services.swarmpool import swarmpool_service
from services.ipfs import ipfs_service
from config import get_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


class JobSubmitRequest(BaseModel):
    model: str
    input_cid: str
    name: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    job_id: str
    job_cid: str
    model: str
    input_cid: str
    status: str
    name: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    proof_cid: Optional[str]
    output_cid: Optional[str]
    confidence: Optional[float]
    provider: Optional[str]


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int


@router.post("/submit", response_model=JobResponse)
async def submit_job(
    request: JobSubmitRequest,
    client: dict = Depends(get_current_client)
):
    """
    Submit a new inference job to SwarmPool.

    Deducts from balance or free trial.
    """
    # Check balance
    can_submit = (
        client.get("free_scans_remaining", 0) > 0 or
        client.get("balance", 0) >= settings.price_per_scan
    )

    if not can_submit:
        raise HTTPException(402, "Insufficient balance. Please add funds.")

    # Get client identity
    client_ens = client.get("ens") or client["wallet"]

    # Submit to SwarmPool
    try:
        result = await swarmpool_service.submit_job(
            client_ens=client_ens,
            model=request.model,
            input_cid=request.input_cid,
            amount=settings.price_per_scan,
            private_key=settings.client_private_key or None
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to submit job: {str(e)}")

    job_data = result["job"]
    job_cid = result["cid"]

    # Create job record
    job_record = {
        "job_id": job_data["job_id"],
        "job_cid": job_cid,
        "model": request.model,
        "input_cid": request.input_cid,
        "name": request.name,
        "status": "pending",
        "client_wallet": client["wallet"],
        "client_ens": client_ens,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "proof_cid": None,
        "output_cid": None,
        "confidence": None,
        "provider": None,
        "cost": settings.price_per_scan
    }

    jobs = get_jobs_collection()
    result = await jobs.insert_one(job_record)
    job_record["id"] = str(result.inserted_id)

    # Deduct balance
    clients = get_clients_collection()
    if client.get("free_scans_remaining", 0) > 0:
        await clients.update_one(
            {"wallet": client["wallet"]},
            {
                "$inc": {"free_scans_remaining": -1, "total_jobs": 1}
            }
        )
    else:
        await clients.update_one(
            {"wallet": client["wallet"]},
            {
                "$inc": {"balance": -settings.price_per_scan, "total_jobs": 1}
            }
        )

    return job_record


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    client: dict = Depends(get_current_client)
):
    """List client's jobs with pagination and filters"""
    jobs = get_jobs_collection()

    # Build query
    query = {"client_wallet": client["wallet"]}
    if status:
        query["status"] = status

    # Get total
    total = await jobs.count_documents(query)

    # Get page
    cursor = jobs.find(query).sort("created_at", -1).skip((page - 1) * per_page).limit(per_page)
    job_list = []
    async for job in cursor:
        job["id"] = str(job["_id"])
        del job["_id"]
        job_list.append(job)

    return {
        "jobs": job_list,
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    client: dict = Depends(get_current_client)
):
    """Get job details"""
    jobs = get_jobs_collection()
    job = await jobs.find_one({
        "job_id": job_id,
        "client_wallet": client["wallet"]
    })

    if not job:
        raise HTTPException(404, "Job not found")

    job["id"] = str(job["_id"])
    del job["_id"]

    return job


@router.post("/{job_id}/refresh")
async def refresh_job_status(
    job_id: str,
    client: dict = Depends(get_current_client)
):
    """
    Refresh job status by checking for proofs.

    In production: webhook or pubsub would push updates.
    """
    jobs = get_jobs_collection()
    job = await jobs.find_one({
        "job_id": job_id,
        "client_wallet": client["wallet"]
    })

    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] == "completed":
        return {"status": "completed", "message": "Already completed"}

    # Check for proof in /swarmpool/proofs/
    # This is simplified - real implementation would check IPFS
    proof = await swarmpool_service.get_job_status(job_id)

    if proof:
        # Update job with proof data
        await jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "proof_cid": proof.get("proof_cid"),
                    "output_cid": proof.get("output_cid"),
                    "confidence": proof.get("confidence"),
                    "provider": proof.get("provider")
                }
            }
        )
        return {"status": "completed", "proof": proof}

    return {"status": job["status"], "message": "Still processing"}
