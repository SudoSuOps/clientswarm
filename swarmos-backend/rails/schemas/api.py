"""
SwarmOS Rails - Pydantic Schemas

API request/response schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field


# =============================================================================
# Job Schemas
# =============================================================================

class JobSubmitRequest(BaseModel):
    """Request to submit a new job."""
    job_type: str = Field(..., description="Job type: spine_mri, brain_mri, etc")
    dicom_ref: str = Field(..., description="IPFS reference to DICOM data")
    client_ens: str = Field(..., description="Client ENS name")
    timestamp: int = Field(..., description="Unix timestamp")
    nonce: str = Field(..., description="Unique nonce for this request")
    signature: str = Field(..., description="EIP-191 signature")


class JobSubmitResponse(BaseModel):
    """Response after job submission."""
    job_id: str
    status: str
    epoch_id: str
    fee_usd: str
    message: str


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    epoch_id: str
    client_ens: str
    worker_ens: Optional[str]
    job_type: str
    status: str
    fee_usd: str
    execution_ms: Optional[int]
    dicom_ref: Optional[str]
    result_ref: Optional[str]
    submitted_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class JobReceiptResponse(BaseModel):
    """Merkle receipt for a completed job."""
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


# =============================================================================
# Worker Schemas
# =============================================================================

class WorkerRegisterRequest(BaseModel):
    """Worker registration request."""
    ens: str = Field(..., description="Worker ENS name")
    gpu_model: str = Field(..., description="GPU model name")
    vram_gb: int = Field(..., description="VRAM in GB")
    cuda_version: Optional[str] = None
    ip_address: str = Field(..., description="LAN IP address")
    signature: str = Field(..., description="Signature proving ENS ownership")


class WorkerHeartbeatRequest(BaseModel):
    """Worker heartbeat."""
    ens: str
    status: str = "online"  # online, busy, draining
    current_job_id: Optional[str] = None
    gpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None


class WorkerHeartbeatResponse(BaseModel):
    """Heartbeat response."""
    acknowledged: bool
    server_time: datetime


class JobClaimResponse(BaseModel):
    """Response when worker claims a job."""
    job_id: Optional[str]
    job_type: Optional[str]
    client_ens: Optional[str]
    dicom_ref: Optional[str]
    claimed: bool
    message: str


class JobCompleteRequest(BaseModel):
    """Worker submits job completion."""
    job_id: str
    worker_ens: str
    result_ref: str = Field(..., description="IPFS reference to result")
    poe_hash: str = Field(..., description="Proof of Execution hash")
    execution_ms: int = Field(..., description="Execution time in ms")
    signature: str = Field(..., description="Worker signature")


# =============================================================================
# Client Schemas
# =============================================================================

class ClientInfoResponse(BaseModel):
    """Client account info."""
    ens: str
    balance_usd: str
    reserved_usd: str
    available_usd: str
    total_spent_usd: str
    total_jobs: int
    scans_available: int  # balance / 0.10
    display_name: Optional[str]
    created_at: datetime


class ClientTopupRequest(BaseModel):
    """Record a client topup from L1."""
    client_ens: str
    amount_usd: str
    eth_tx_hash: str = Field(..., description="L1 transaction hash")


class ClientTopupResponse(BaseModel):
    """Topup confirmation."""
    client_ens: str
    amount_usd: str
    new_balance_usd: str
    scans_available: int
    tx_hash: str


class TransactionHistoryItem(BaseModel):
    """A single transaction in history."""
    tx_type: str
    amount_usd: str
    balance_after: str
    reference: Optional[str]
    eth_tx_hash: Optional[str]
    created_at: datetime


# =============================================================================
# Epoch Schemas
# =============================================================================

class EpochSummaryResponse(BaseModel):
    """Epoch summary."""
    epoch_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    jobs_count: int
    jobs_merkle_root: Optional[str]
    total_revenue: str
    total_distributed: str
    ipfs_hash: Optional[str]


class EpochDetailResponse(BaseModel):
    """Detailed epoch info."""
    epoch_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    jobs_count: int
    jobs_merkle_root: Optional[str]
    treasury: dict
    agents: dict
    clients: dict
    ipfs_hash: Optional[str]


class CurrentEpochResponse(BaseModel):
    """Current active epoch status."""
    epoch_id: str
    status: str
    start_time: datetime
    jobs_completed: int
    revenue_usd: str
    agents_online: int
    queue_depth: int


# =============================================================================
# System Schemas
# =============================================================================

class SystemStatusResponse(BaseModel):
    """System-wide status."""
    status: str  # healthy, degraded, down
    current_epoch: str
    uptime_seconds: int
    queue_depth: int
    processing: int
    workers_online: int
    workers_busy: int
    total_jobs_today: int
    total_revenue_today: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    components: dict  # redis, db, ipfs status
