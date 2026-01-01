"""
IPFS Service for ClientSwarm
"""
import json
import httpx
from typing import Any, Dict, Optional, List

from config import get_settings

settings = get_settings()


class IPFSService:
    """IPFS client for file uploads and job publishing"""

    def __init__(self):
        self.api_url = settings.ipfs_api.rstrip("/")
        self.api_base = f"{self.api_url}/api/v0"

    async def check_connection(self) -> bool:
        """Check IPFS daemon connection"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.api_base}/id", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False

    async def upload_file(self, file_bytes: bytes, filename: str) -> str:
        """Upload file to IPFS, return CID"""
        async with httpx.AsyncClient() as client:
            files = {"file": (filename, file_bytes)}
            resp = await client.post(
                f"{self.api_base}/add",
                files=files,
                params={"cid-version": "1"},
                timeout=60.0
            )
            resp.raise_for_status()
            result = resp.json()
            return result["Hash"]

    async def upload_json(self, data: Dict[str, Any]) -> str:
        """Upload JSON to IPFS, return CID"""
        json_bytes = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
        return await self.upload_file(json_bytes, "data.json")

    async def fetch_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """Fetch JSON from IPFS by CID"""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.api_base}/cat",
                    params={"arg": cid},
                    timeout=30.0
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

            # Fallback to gateway
            try:
                resp = await client.get(
                    f"{settings.ipfs_gateway}/{cid}",
                    timeout=30.0
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass

        return None

    async def write_to_mfs(self, mfs_path: str, cid: str) -> bool:
        """Copy CID to MFS path"""
        async with httpx.AsyncClient() as client:
            try:
                # Remove if exists
                await client.post(
                    f"{self.api_base}/files/rm",
                    params={"arg": mfs_path, "force": "true"}
                )
            except Exception:
                pass

            try:
                resp = await client.post(
                    f"{self.api_base}/files/cp?arg=/ipfs/{cid}&arg={mfs_path}",
                    timeout=10.0
                )
                return resp.status_code == 200
            except Exception:
                return False

    async def publish_job(self, job_data: Dict[str, Any]) -> str:
        """Publish job to SwarmPool"""
        cid = await self.upload_json(job_data)
        job_id = job_data.get("job_id", "unknown")
        mfs_path = f"/swarmpool/jobs/{job_id}.json"
        await self.write_to_mfs(mfs_path, cid)
        return cid

    async def pubsub_publish(self, topic: str, data: Dict[str, Any]) -> bool:
        """Publish to IPFS pubsub"""
        import base64
        async with httpx.AsyncClient() as client:
            try:
                json_str = json.dumps(data)
                encoded = base64.b64encode(json_str.encode()).decode()
                resp = await client.post(
                    f"{self.api_base}/pubsub/pub",
                    params={"arg": topic},
                    data=encoded,
                    timeout=5.0
                )
                return resp.status_code == 200
            except Exception:
                return False


# Singleton
ipfs_service = IPFSService()
