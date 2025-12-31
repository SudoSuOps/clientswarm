"""
SwarmOS Bee-2 Worker

The worker. The miner. The GPU operator.

This daemon:
- Registers with Bee-1 controller
- Sends heartbeats
- Claims and executes jobs
- Returns results with Proof of Execution
- Generates PDF reports via QueenBee Medical AI
"""

import os
import sys
import time
import asyncio
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

import httpx


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class WorkerConfig:
    """Worker configuration."""
    # Identity
    ens: str = os.getenv("WORKER_ENS", "bumble70b.swarmbee.eth")
    private_key: str = os.getenv("WORKER_PRIVATE_KEY", "")

    # Hardware
    gpu_model: str = os.getenv("GPU_MODEL", "RTX 5090")
    vram_gb: int = int(os.getenv("VRAM_GB", "32"))
    cuda_version: str = os.getenv("CUDA_VERSION", "12.4")

    # Network
    bee1_url: str = os.getenv("BEE1_URL", "http://localhost:8001")
    queenbee_url: str = os.getenv("QUEENBEE_URL", "http://localhost:8000")
    ip_address: str = os.getenv("WORKER_IP", "10.0.0.10")

    # Output
    output_dir: str = os.getenv("OUTPUT_DIR", "/tmp/swarmos-results")

    # Behavior
    heartbeat_interval: int = 30  # seconds
    poll_interval: int = 2  # seconds between job polls
    max_retries: int = 3


config = WorkerConfig()

# Ensure output directory exists
Path(config.output_dir).mkdir(parents=True, exist_ok=True)


# =============================================================================
# Inference Executors
# =============================================================================

class BaseInferenceExecutor:
    """Base class for inference executors."""

    job_type: str = "base"

    async def execute(self, dicom_ref: str, job_id: str = None) -> dict:
        """
        Execute inference on DICOM data.

        Args:
            dicom_ref: IPFS reference to DICOM data
            job_id: Job identifier

        Returns:
            dict with result_ref and execution metadata
        """
        raise NotImplementedError


class SpineMRIExecutor(BaseInferenceExecutor):
    """Spine MRI analysis using QueenBee-Spine model."""

    job_type: str = "spine_mri"

    async def execute(self, dicom_ref: str, job_id: str = None) -> dict:
        """Execute spine MRI analysis via QueenBee Medical AI."""
        start_time = time.time()

        # Sample findings for demo (in production: extract from DICOM)
        sample_findings = [
            "L3-L4: Mild disc bulge without significant canal stenosis.",
            "L4-L5: Moderate central canal stenosis with ligamentum flavum hypertrophy. Moderate bilateral foraminal narrowing.",
            "L5-S1: Mild disc desiccation. Mild bilateral foraminal narrowing.",
        ]
        findings_text = " ".join(sample_findings)

        # Call real QueenBee inference
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{config.queenbee_url}/spine-report",
                    json={
                        "findings": findings_text,
                        "k_samples": 7,
                        "max_new_tokens": 512,
                    }
                )
                response.raise_for_status()
                inference_result = response.json()
            except Exception as e:
                print(f"⚠️  QueenBee inference failed: {e}, using fallback")
                inference_result = {
                    "impression": ["Unable to process - service unavailable"],
                    "stenosis_grades": {},
                    "confidence": {"score_0_100": 0, "method": "fallback"},
                    "recommendation": ["Retry or manual review required"],
                }

        execution_ms = int((time.time() - start_time) * 1000)

        # Build structured result
        result = {
            "job_type": self.job_type,
            "job_id": job_id,
            "model": "Med42-70B + QueenBee-Spine-LoRA",
            "input_ref": dicom_ref,
            "inference": inference_result,
            "stenosis_grades": inference_result.get("stenosis_grades", {}),
            "impression": inference_result.get("impression", []),
            "confidence": inference_result.get("confidence", {}),
            "recommendation": inference_result.get("recommendation", []),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "execution_ms": execution_ms,
        }

        # Generate PDF report
        pdf_path = await self.generate_pdf(result, job_id)

        # Upload to IPFS
        result_ref = await self.upload_to_ipfs(result, pdf_path, job_id)

        return {
            "result": result,
            "result_ref": result_ref,
            "pdf_path": pdf_path,
            "execution_ms": execution_ms,
        }

    async def generate_pdf(self, result: dict, job_id: str) -> str:
        """Generate PDF report from inference result."""
        pdf_path = Path(config.output_dir) / f"{job_id}_report.pdf"
        html_path = Path(config.output_dir) / f"{job_id}_report.html"

        # Build HTML report
        stenosis_rows = ""
        for level, grade in result.get("stenosis_grades", {}).items():
            color = {"Normal": "#10b981", "Mild": "#f59e0b", "Moderate": "#f97316", "Severe": "#ef4444"}.get(grade, "#888")
            stenosis_rows += f"<tr><td>{level}</td><td style='color:{color};font-weight:bold'>{grade}</td></tr>"

        impressions = "".join(f"<li>{imp}</li>" for imp in result.get("impression", []))
        recommendations = "".join(f"<li>{rec}</li>" for rec in result.get("recommendation", []))
        confidence = result.get("confidence", {})

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Spine MRI Analysis Report - {job_id}</title>
    <style>
        body {{ font-family: 'Helvetica', sans-serif; margin: 40px; color: #1a1a1a; }}
        .header {{ border-bottom: 3px solid #10b981; padding-bottom: 20px; margin-bottom: 30px; }}
        .logo {{ font-size: 24px; font-weight: bold; color: #10b981; }}
        .job-id {{ color: #666; font-size: 14px; }}
        h2 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f8f8; }}
        .confidence {{ background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
        ul {{ line-height: 1.8; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">SwarmOS Medical AI</div>
        <div class="job-id">Report ID: {job_id} | Generated: {result.get('processed_at', 'N/A')}</div>
    </div>

    <h2>Stenosis Grading by Level</h2>
    <table>
        <tr><th>Spinal Level</th><th>Stenosis Grade</th></tr>
        {stenosis_rows}
    </table>

    <h2>Clinical Impression</h2>
    <ul>{impressions}</ul>

    <h2>Recommendations</h2>
    <ul>{recommendations}</ul>

    <div class="confidence">
        <strong>AI Confidence:</strong> {confidence.get('score_0_100', 'N/A')}%
        (Method: {confidence.get('method', 'N/A')})
    </div>

    <div class="footer">
        <p><strong>Model:</strong> {result.get('model', 'N/A')}</p>
        <p><strong>Processing Time:</strong> {result.get('execution_ms', 'N/A')}ms</p>
        <p><strong>DICOM Reference:</strong> {result.get('input_ref', 'N/A')}</p>
        <p style="margin-top:20px"><em>This report was generated by SwarmOS sovereign compute infrastructure.
        Results should be validated by a qualified radiologist.</em></p>
    </div>
</body>
</html>"""

        # Write HTML
        html_path.write_text(html_content)

        # Convert to PDF using wkhtmltopdf or weasyprint if available
        try:
            subprocess.run(
                ["wkhtmltopdf", "--quiet", str(html_path), str(pdf_path)],
                check=True, capture_output=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: just keep HTML, rename to .pdf for now
            pdf_path = html_path.with_suffix('.html')

        return str(pdf_path)

    async def upload_to_ipfs(self, result: dict, pdf_path: str, job_id: str) -> str:
        """Upload result and PDF to IPFS."""
        # Save JSON result
        json_path = Path(config.output_dir) / f"{job_id}_result.json"
        json_path.write_text(json.dumps(result, indent=2))

        # Try to add to IPFS
        try:
            proc = subprocess.run(
                ["ipfs", "add", "-Q", "--cid-version=1", str(pdf_path)],
                capture_output=True, text=True, check=True
            )
            cid = proc.stdout.strip()
            return f"ipfs://{cid}"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: generate hash-based reference
            result_hash = hashlib.sha256(json.dumps(result).encode()).hexdigest()[:44]
            return f"ipfs://Qm{result_hash}"


class BrainMRIExecutor(BaseInferenceExecutor):
    """Brain MRI segmentation."""

    job_type: str = "brain_mri"

    async def execute(self, dicom_ref: str, job_id: str = None) -> dict:
        """Execute brain MRI segmentation."""
        start_time = time.time()

        # Simulated inference (would use real model in production)
        await asyncio.sleep(3.0)

        execution_ms = int((time.time() - start_time) * 1000)

        result = {
            "job_type": self.job_type,
            "job_id": job_id,
            "model": "BrainSeg-v2.0",
            "input_ref": dicom_ref,
            "segmentation": {
                "white_matter_vol_ml": 485.2,
                "gray_matter_vol_ml": 612.8,
                "csf_vol_ml": 142.1,
                "lesion_count": 0,
            },
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "execution_ms": execution_ms,
        }

        result_ref = f"ipfs://Qm{hashlib.sha256(json.dumps(result).encode()).hexdigest()[:44]}"

        return {
            "result": result,
            "result_ref": result_ref,
            "execution_ms": execution_ms,
        }


class ClinicalReportExecutor(BaseInferenceExecutor):
    """Clinical report generation."""

    job_type: str = "clinical_report"

    async def execute(self, dicom_ref: str, job_id: str = None) -> dict:
        """Generate clinical report."""
        start_time = time.time()

        # Simulated report generation
        await asyncio.sleep(1.5)

        execution_ms = int((time.time() - start_time) * 1000)

        result = {
            "job_type": self.job_type,
            "job_id": job_id,
            "model": "ReportGen-v1.0",
            "input_ref": dicom_ref,
            "report": {
                "impression": "Moderate central canal stenosis at L4-L5 level...",
                "findings": "...",
                "recommendation": "Clinical correlation recommended.",
            },
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "execution_ms": execution_ms,
        }

        result_ref = f"ipfs://Qm{hashlib.sha256(json.dumps(result).encode()).hexdigest()[:44]}"

        return {
            "result": result,
            "result_ref": result_ref,
            "execution_ms": execution_ms,
        }


# Executor registry
EXECUTORS = {
    "spine_mri": SpineMRIExecutor(),
    "brain_mri": BrainMRIExecutor(),
    "clinical_report": ClinicalReportExecutor(),
}


# =============================================================================
# Worker Daemon
# =============================================================================

class BeeWorker:
    """
    Bee-2 Worker Daemon.
    
    Lifecycle:
    1. Register with Bee-1
    2. Start heartbeat loop
    3. Poll for jobs
    4. Execute jobs
    5. Submit results
    """
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.bee1_url,
            timeout=30.0,
            headers={"X-Worker-ENS": config.ens}
        )
        self.running = False
        self.current_job_id: Optional[str] = None
        self.jobs_completed = 0
        self.jobs_failed = 0
    
    async def start(self):
        """Start the worker daemon."""
        print(f"🐝 Bee-2 Worker starting...")
        print(f"   ENS: {self.config.ens}")
        print(f"   GPU: {self.config.gpu_model} ({self.config.vram_gb}GB)")
        print(f"   Bee-1: {self.config.bee1_url}")
        
        # Register with Bee-1
        await self.register()
        
        self.running = True
        
        # Start background tasks
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        job_task = asyncio.create_task(self.job_loop())
        
        print(f"   ✓ Worker ready")
        
        try:
            await asyncio.gather(heartbeat_task, job_task)
        except asyncio.CancelledError:
            print("Worker shutting down...")
        finally:
            self.running = False
            await self.client.aclose()
    
    async def register(self):
        """Register with Bee-1 controller."""
        try:
            response = await self.client.post(
                "/api/v1/workers/register",
                json={
                    "ens": self.config.ens,
                    "gpu_model": self.config.gpu_model,
                    "vram_gb": self.config.vram_gb,
                    "cuda_version": self.config.cuda_version,
                    "ip_address": self.config.ip_address,
                    "signature": "0x...",  # Would be real signature
                }
            )
            response.raise_for_status()
            print(f"   ✓ Registered with Bee-1")
        except Exception as e:
            print(f"   ✗ Registration failed: {e}")
            raise
    
    async def heartbeat_loop(self):
        """Send periodic heartbeats to Bee-1."""
        while self.running:
            try:
                status = "busy" if self.current_job_id else "online"
                
                response = await self.client.post(
                    "/api/v1/workers/heartbeat",
                    json={
                        "ens": self.config.ens,
                        "status": status,
                        "current_job_id": self.current_job_id,
                    }
                )
                response.raise_for_status()
                
            except Exception as e:
                print(f"⚠️  Heartbeat failed: {e}")
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def job_loop(self):
        """Poll for and execute jobs."""
        while self.running:
            if self.current_job_id:
                # Already processing a job
                await asyncio.sleep(self.config.poll_interval)
                continue
            
            try:
                # Try to claim a job
                job = await self.claim_job()
                
                if job:
                    await self.execute_job(job)
                else:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(self.config.poll_interval)
                    
            except Exception as e:
                print(f"⚠️  Job loop error: {e}")
                await asyncio.sleep(self.config.poll_interval)
    
    async def claim_job(self) -> Optional[dict]:
        """Try to claim a job from the queue."""
        try:
            response = await self.client.post("/api/v1/jobs/claim")
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("claimed"):
                print(f"📥 Claimed job: {data['job_id']} ({data['job_type']})")
                return data
            
            return None
            
        except Exception as e:
            print(f"⚠️  Claim failed: {e}")
            return None
    
    async def execute_job(self, job: dict):
        """Execute a claimed job."""
        job_id = job["job_id"]
        job_type = job["job_type"]
        dicom_ref = job["dicom_ref"]
        
        self.current_job_id = job_id
        
        try:
            print(f"⚡ Executing {job_id}...")
            
            # Get executor for job type
            executor = EXECUTORS.get(job_type)
            if not executor:
                raise ValueError(f"Unknown job type: {job_type}")
            
            # Execute inference
            result = await executor.execute(dicom_ref, job_id=job_id)
            
            # Generate Proof of Execution
            poe_data = f"{job_id}:{result['result_ref']}:{self.config.ens}"
            poe_hash = hashlib.sha256(poe_data.encode()).hexdigest()
            
            # Submit completion
            await self.submit_completion(
                job_id=job_id,
                result_ref=result["result_ref"],
                poe_hash=poe_hash,
                execution_ms=result["execution_ms"],
            )
            
            self.jobs_completed += 1
            print(f"✅ Completed {job_id} in {result['execution_ms']}ms")
            
        except Exception as e:
            self.jobs_failed += 1
            print(f"❌ Failed {job_id}: {e}")
            # TODO: Report failure to Bee-1
            
        finally:
            self.current_job_id = None
    
    async def submit_completion(
        self,
        job_id: str,
        result_ref: str,
        poe_hash: str,
        execution_ms: int,
    ):
        """Submit job completion to Bee-1."""
        response = await self.client.post(
            f"/api/v1/jobs/{job_id}/complete",
            json={
                "job_id": job_id,
                "worker_ens": self.config.ens,
                "result_ref": result_ref,
                "poe_hash": poe_hash,
                "execution_ms": execution_ms,
                "signature": "0x...",  # Would be real signature
            }
        )
        response.raise_for_status()


# =============================================================================
# Main
# =============================================================================

async def main():
    """Main entry point."""
    worker = BeeWorker(config)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n👋 Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
