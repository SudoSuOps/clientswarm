"""
SwarmOS Rails - Database Models

SQLAlchemy models for the SwarmLedger database.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Text, ForeignKey, Index, Enum
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EpochStatus(str, enum.Enum):
    ACTIVE = "active"
    SEALING = "sealing"
    FINALIZED = "finalized"


class WorkerStatus(str, enum.Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"
    DRAINING = "draining"


class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"


class TxType(str, enum.Enum):
    DEPOSIT = "deposit"
    JOB_CHARGE = "job_charge"
    JOB_REFUND = "job_refund"
    WITHDRAWAL = "withdrawal"


# =============================================================================
# Models
# =============================================================================

class Job(Base):
    """A compute job submitted by a client."""
    
    __tablename__ = "jobs"
    
    id = Column(String(32), primary_key=True)  # job-002-0848
    epoch_id = Column(String(16), ForeignKey("epochs.id"), nullable=False)
    client_ens = Column(String(128), ForeignKey("clients.ens"), nullable=False)
    worker_ens = Column(String(128), ForeignKey("workers.ens"), nullable=True)
    
    job_type = Column(String(64), nullable=False)  # spine_mri, brain_mri, etc
    status = Column(String(16), default=JobStatus.PENDING.value, nullable=False)
    
    dicom_ref = Column(String(256), nullable=True)   # ipfs://Qm...
    result_ref = Column(String(256), nullable=True)  # ipfs://Qm...
    poe_hash = Column(String(64), nullable=True)     # proof of execution
    
    fee_usd = Column(Numeric(10, 2), default=Decimal("0.10"))
    execution_ms = Column(Integer, nullable=True)
    
    submitted_at = Column(DateTime, nullable=False, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    epoch = relationship("Epoch", back_populates="jobs")
    client = relationship("Client", back_populates="jobs")
    worker = relationship("Worker", back_populates="jobs")
    
    __table_args__ = (
        Index("ix_jobs_epoch_id", "epoch_id"),
        Index("ix_jobs_client_ens", "client_ens"),
        Index("ix_jobs_worker_ens", "worker_ens"),
        Index("ix_jobs_status", "status"),
    )


class Epoch(Base):
    """A sealed compute epoch (like a block)."""
    
    __tablename__ = "epochs"
    
    id = Column(String(16), primary_key=True)  # epoch-002
    status = Column(String(16), default=EpochStatus.ACTIVE.value, nullable=False)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    
    jobs_count = Column(Integer, default=0)
    jobs_merkle_root = Column(String(64), nullable=True)
    
    total_revenue = Column(Numeric(10, 2), default=Decimal("0"))
    work_pool = Column(Numeric(10, 2), default=Decimal("0"))
    readiness_pool = Column(Numeric(10, 2), default=Decimal("0"))
    protocol_fee = Column(Numeric(10, 2), default=Decimal("0"))
    operator_fee = Column(Numeric(10, 2), default=Decimal("0"))
    total_distributed = Column(Numeric(10, 2), default=Decimal("0"))
    
    signature = Column(Text, nullable=True)  # EIP-191 signature
    ipfs_hash = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    sealed_at = Column(DateTime, nullable=True)
    
    # Relationships
    jobs = relationship("Job", back_populates="epoch")
    payouts = relationship("Payout", back_populates="epoch")


class Client(Base):
    """A client account (clinic, etc)."""
    
    __tablename__ = "clients"
    
    ens = Column(String(128), primary_key=True)  # xyz.clientswarm.eth
    
    balance_usd = Column(Numeric(10, 2), default=Decimal("0"))
    reserved_usd = Column(Numeric(10, 2), default=Decimal("0"))  # Pending jobs
    total_spent_usd = Column(Numeric(10, 2), default=Decimal("0"))
    total_jobs = Column(Integer, default=0)
    
    display_name = Column(String(256), nullable=True)
    contact_email = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    jobs = relationship("Job", back_populates="client")
    transactions = relationship("CreditTransaction", back_populates="client")


class Worker(Base):
    """A worker node (Bee-2...N)."""
    
    __tablename__ = "workers"
    
    ens = Column(String(128), primary_key=True)  # bee-01.swarmbee.eth
    
    status = Column(String(16), default=WorkerStatus.OFFLINE.value, nullable=False)
    gpu_model = Column(String(64), nullable=True)
    vram_gb = Column(Integer, nullable=True)
    cuda_version = Column(String(16), nullable=True)
    
    current_job_id = Column(String(32), nullable=True)
    
    jobs_completed = Column(Integer, default=0)
    jobs_failed = Column(Integer, default=0)
    total_earned_usd = Column(Numeric(10, 2), default=Decimal("0"))
    uptime_seconds = Column(Integer, default=0)
    
    ip_address = Column(String(45), nullable=True)  # LAN IP
    last_heartbeat = Column(DateTime, nullable=True)
    registered_at = Column(DateTime, default=func.now())
    
    # Relationships
    jobs = relationship("Job", back_populates="worker")
    payouts = relationship("Payout", back_populates="worker")
    
    __table_args__ = (
        Index("ix_workers_status", "status"),
    )


class Payout(Base):
    """Payout record for a worker in an epoch."""
    
    __tablename__ = "payouts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    epoch_id = Column(String(16), ForeignKey("epochs.id"), nullable=False)
    worker_ens = Column(String(128), ForeignKey("workers.ens"), nullable=False)
    
    jobs_completed = Column(Integer, default=0)
    uptime_seconds = Column(Integer, default=0)
    poe_success_rate = Column(Numeric(5, 4), default=Decimal("1.0"))
    
    work_share_usd = Column(Numeric(10, 2), default=Decimal("0"))
    readiness_share_usd = Column(Numeric(10, 2), default=Decimal("0"))
    total_payout_usd = Column(Numeric(10, 2), default=Decimal("0"))
    
    status = Column(String(16), default=PayoutStatus.PENDING.value)
    paid_at = Column(DateTime, nullable=True)
    tx_hash = Column(String(66), nullable=True)  # L1 tx hash if paid on-chain
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    epoch = relationship("Epoch", back_populates="payouts")
    worker = relationship("Worker", back_populates="payouts")
    
    __table_args__ = (
        Index("ix_payouts_epoch_id", "epoch_id"),
        Index("ix_payouts_worker_ens", "worker_ens"),
    )


class CreditTransaction(Base):
    """Client balance transaction record."""
    
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_ens = Column(String(128), ForeignKey("clients.ens"), nullable=False)
    
    tx_type = Column(String(16), nullable=False)  # deposit, job_charge, etc
    amount_usd = Column(Numeric(10, 2), nullable=False)
    balance_after = Column(Numeric(10, 2), nullable=False)
    
    reference = Column(String(64), nullable=True)  # job_id or external ref
    eth_tx_hash = Column(String(66), nullable=True)  # L1 tx hash
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    client = relationship("Client", back_populates="transactions")
    
    __table_args__ = (
        Index("ix_credit_tx_client_ens", "client_ens"),
        Index("ix_credit_tx_type", "tx_type"),
    )


# =============================================================================
# Utilities
# =============================================================================

def generate_job_id(epoch_id: str, sequence: int) -> str:
    """Generate job ID like job-002-0848"""
    epoch_num = epoch_id.split("-")[1]
    return f"job-{epoch_num}-{sequence:04d}"


def generate_epoch_id(sequence: int) -> str:
    """Generate epoch ID like epoch-002"""
    return f"epoch-{sequence:03d}"
