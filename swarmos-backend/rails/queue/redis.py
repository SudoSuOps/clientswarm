"""
SwarmOS Rails - Redis Queue

Job queue and worker management using Redis.
"""

import json
import time
from typing import Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import redis.asyncio as redis


@dataclass
class QueuedJob:
    """A job in the queue."""
    job_id: str
    job_type: str
    client_ens: str
    dicom_ref: str
    fee_usd: str
    queued_at: float
    priority: int = 0  # Higher = more urgent


@dataclass 
class WorkerInfo:
    """Worker registration info."""
    ens: str
    status: str  # online, busy, offline
    gpu_model: str
    vram_gb: int
    ip_address: str
    current_job_id: Optional[str] = None
    last_heartbeat: float = 0


class SwarmQueue:
    """
    Redis-based job queue for SwarmOS.
    
    Uses Redis Streams for reliable job processing.
    """
    
    JOBS_STREAM = "swarm:jobs:pending"
    JOBS_PROCESSING = "swarm:jobs:processing"
    WORKERS_HASH = "swarm:workers"
    WORKER_HEARTBEAT_TTL = 60  # seconds
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
    
    @property
    def redis(self) -> redis.Redis:
        if not self._redis:
            raise RuntimeError("Not connected to Redis")
        return self._redis
    
    # =========================================================================
    # Job Queue Operations
    # =========================================================================
    
    async def enqueue_job(self, job: QueuedJob) -> str:
        """
        Add a job to the queue.
        
        Returns:
            Redis stream message ID
        """
        data = {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "client_ens": job.client_ens,
            "dicom_ref": job.dicom_ref,
            "fee_usd": job.fee_usd,
            "queued_at": str(job.queued_at),
            "priority": str(job.priority),
        }
        
        message_id = await self.redis.xadd(self.JOBS_STREAM, data)
        return message_id
    
    async def claim_job(self, worker_ens: str) -> Optional[QueuedJob]:
        """
        Claim the next available job for a worker.
        
        Returns:
            QueuedJob if available, None otherwise
        """
        # Read one message from stream
        messages = await self.redis.xread(
            {self.JOBS_STREAM: "0"},
            count=1,
            block=1000  # 1 second timeout
        )
        
        if not messages:
            return None
        
        stream_name, entries = messages[0]
        if not entries:
            return None
        
        message_id, data = entries[0]
        
        # Move to processing set
        await self.redis.hset(
            self.JOBS_PROCESSING,
            data["job_id"],
            json.dumps({
                "worker_ens": worker_ens,
                "claimed_at": time.time(),
                "message_id": message_id,
            })
        )
        
        # Remove from pending stream
        await self.redis.xdel(self.JOBS_STREAM, message_id)
        
        return QueuedJob(
            job_id=data["job_id"],
            job_type=data["job_type"],
            client_ens=data["client_ens"],
            dicom_ref=data["dicom_ref"],
            fee_usd=data["fee_usd"],
            queued_at=float(data["queued_at"]),
            priority=int(data.get("priority", 0)),
        )
    
    async def complete_job(self, job_id: str) -> bool:
        """Mark a job as completed and remove from processing."""
        removed = await self.redis.hdel(self.JOBS_PROCESSING, job_id)
        return removed > 0
    
    async def fail_job(self, job_id: str, requeue: bool = True) -> bool:
        """
        Mark a job as failed.
        
        Args:
            job_id: The job ID
            requeue: If True, put back in queue for retry
        """
        processing_data = await self.redis.hget(self.JOBS_PROCESSING, job_id)
        
        if processing_data:
            await self.redis.hdel(self.JOBS_PROCESSING, job_id)
            
            if requeue:
                # Re-add to queue (would need original job data)
                # For now, just log that it failed
                pass
        
        return True
    
    async def get_queue_depth(self) -> int:
        """Get number of jobs waiting in queue."""
        return await self.redis.xlen(self.JOBS_STREAM)
    
    async def get_processing_count(self) -> int:
        """Get number of jobs currently being processed."""
        return await self.redis.hlen(self.JOBS_PROCESSING)
    
    # =========================================================================
    # Worker Registry Operations
    # =========================================================================
    
    async def register_worker(self, worker: WorkerInfo) -> None:
        """Register or update a worker."""
        worker.last_heartbeat = time.time()
        await self.redis.hset(
            self.WORKERS_HASH,
            worker.ens,
            json.dumps(asdict(worker))
        )
    
    async def update_heartbeat(self, worker_ens: str) -> bool:
        """Update worker heartbeat timestamp."""
        data = await self.redis.hget(self.WORKERS_HASH, worker_ens)
        if not data:
            return False
        
        worker_data = json.loads(data)
        worker_data["last_heartbeat"] = time.time()
        await self.redis.hset(self.WORKERS_HASH, worker_ens, json.dumps(worker_data))
        return True
    
    async def set_worker_status(
        self,
        worker_ens: str,
        status: str,
        current_job_id: Optional[str] = None
    ) -> bool:
        """Update worker status."""
        data = await self.redis.hget(self.WORKERS_HASH, worker_ens)
        if not data:
            return False
        
        worker_data = json.loads(data)
        worker_data["status"] = status
        worker_data["current_job_id"] = current_job_id
        worker_data["last_heartbeat"] = time.time()
        await self.redis.hset(self.WORKERS_HASH, worker_ens, json.dumps(worker_data))
        return True
    
    async def get_worker(self, worker_ens: str) -> Optional[WorkerInfo]:
        """Get worker info."""
        data = await self.redis.hget(self.WORKERS_HASH, worker_ens)
        if not data:
            return None
        
        worker_data = json.loads(data)
        return WorkerInfo(**worker_data)
    
    async def get_all_workers(self) -> list[WorkerInfo]:
        """Get all registered workers."""
        all_data = await self.redis.hgetall(self.WORKERS_HASH)
        workers = []
        
        for ens, data in all_data.items():
            worker_data = json.loads(data)
            workers.append(WorkerInfo(**worker_data))
        
        return workers
    
    async def get_online_workers(self) -> list[WorkerInfo]:
        """Get workers that are online and not busy."""
        all_workers = await self.get_all_workers()
        now = time.time()
        
        return [
            w for w in all_workers
            if w.status == "online"
            and (now - w.last_heartbeat) < self.WORKER_HEARTBEAT_TTL
        ]
    
    async def get_available_worker(self) -> Optional[WorkerInfo]:
        """Get next available worker for job assignment."""
        online = await self.get_online_workers()
        
        if not online:
            return None
        
        # Simple round-robin: return first available
        # Could be enhanced with load balancing, GPU matching, etc.
        return online[0]
    
    async def cleanup_stale_workers(self) -> int:
        """Mark workers with stale heartbeats as offline."""
        all_workers = await self.get_all_workers()
        now = time.time()
        cleaned = 0
        
        for worker in all_workers:
            if (now - worker.last_heartbeat) > self.WORKER_HEARTBEAT_TTL:
                if worker.status != "offline":
                    await self.set_worker_status(worker.ens, "offline")
                    cleaned += 1
        
        return cleaned
    
    # =========================================================================
    # Stats
    # =========================================================================
    
    async def get_stats(self) -> dict:
        """Get queue and worker stats."""
        all_workers = await self.get_all_workers()
        now = time.time()
        
        online_count = sum(
            1 for w in all_workers
            if w.status in ("online", "busy")
            and (now - w.last_heartbeat) < self.WORKER_HEARTBEAT_TTL
        )
        
        busy_count = sum(
            1 for w in all_workers
            if w.status == "busy"
            and (now - w.last_heartbeat) < self.WORKER_HEARTBEAT_TTL
        )
        
        return {
            "queue_depth": await self.get_queue_depth(),
            "processing": await self.get_processing_count(),
            "workers_total": len(all_workers),
            "workers_online": online_count,
            "workers_busy": busy_count,
            "workers_available": online_count - busy_count,
        }
