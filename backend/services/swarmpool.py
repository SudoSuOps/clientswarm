"""
SwarmPool Integration Service
"""
import json
import time
from typing import Any, Dict, Optional, List

from config import get_settings
from services.ipfs import ipfs_service
from services.crypto import sign_snapshot, generate_job_id, generate_nonce

settings = get_settings()


class SwarmPoolService:
    """SwarmPool job submission and tracking"""

    async def submit_job(
        self,
        client_ens: str,
        model: str,
        input_cid: str,
        amount: float = 0.10,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a job to SwarmPool.

        Returns job snapshot with CID.
        """
        job_id = generate_job_id()
        timestamp = int(time.time())
        nonce = generate_nonce()

        job = {
            "type": "job",
            "version": "1.0.0",
            "job_id": job_id,
            "job_type": "inference",
            "model": model,
            "input_cid": input_cid,
            "params": {
                "confidence_threshold": 0.70,
                "output_format": "json+pdf"
            },
            "payment": {
                "amount": f"{amount:.2f}",
                "token": "USDC"
            },
            "client": client_ens,
            "timestamp": timestamp,
            "nonce": nonce,
        }

        # Sign if key provided
        if private_key:
            job["sig"] = sign_snapshot(job, private_key)

        # Publish to IPFS
        cid = await ipfs_service.publish_job(job)

        # Announce via pubsub
        await ipfs_service.pubsub_publish(
            f"/{settings.swarmpool_pool}/jobs/new",
            {
                "job_id": job_id,
                "job_cid": cid,
                "model": model,
                "client": client_ens,
                "timestamp": timestamp
            }
        )

        return {
            "job": job,
            "cid": cid
        }

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Check job status by looking for proofs.

        Returns proof if found, None if still pending.
        """
        # Check for proof in /swarmpool/proofs/
        # In production: query IPFS MFS or watch pubsub
        proof_path = f"/swarmpool/proofs/proof-{job_id}.json"

        # Try to fetch proof
        # This is a simplified check - real implementation would
        # watch pubsub or poll the proofs directory
        return None

    async def watch_for_proof(self, job_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Watch for proof completion.

        In production: subscribe to pubsub topic.
        """
        import asyncio

        start = time.time()
        while time.time() - start < timeout:
            proof = await self.get_job_status(job_id)
            if proof:
                return proof
            await asyncio.sleep(5)

        return None


# Singleton
swarmpool_service = SwarmPoolService()
