#!/usr/bin/env python3
"""
SWARMPOOL PROTOCOL TEST
=======================
100 Spinal MRI Scan Orders
Client: dev.clientswarm.eth
Worker: bumble70b.swarmpool.eth

Real protocol. Real data. Real inference.
"""
import asyncio
import aiohttp
import json
import random
from datetime import datetime, timezone
from eth_account import Account
from eth_account.messages import encode_defunct
from siwe import SiweMessage

# Config
API_URL = "http://localhost:8000"
DEV_WALLET = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
DEV_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Spinal MRI scan types
SCAN_TYPES = [
    "cervical_spine",
    "thoracic_spine",
    "lumbar_spine",
    "sacral_spine",
    "full_spine"
]

CLINICAL_INDICATIONS = [
    "chronic_back_pain",
    "radiculopathy",
    "disc_herniation_suspected",
    "spinal_stenosis",
    "post_surgical_eval",
    "trauma",
    "myelopathy",
    "tumor_screening",
    "infection_suspected",
    "degenerative_disease"
]


class ProtocolTest:
    def __init__(self):
        self.session = None
        self.token = None
        self.jobs_submitted = []

    async def login(self):
        """SIWE Login"""
        async with self.session.get(f"{API_URL}/auth/nonce") as resp:
            data = await resp.json()
            nonce = data["nonce"]

        siwe_message = SiweMessage(
            domain="clientswarm.eth",
            address=DEV_WALLET,
            statement="Sign in to ClientSwarm",
            uri="https://clientswarm.eth.limo",
            version="1",
            chain_id=1,
            nonce=nonce,
            issued_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        message = siwe_message.prepare_message()

        account = Account.from_key(DEV_PRIVATE_KEY)
        signable = encode_defunct(text=message)
        signed = account.sign_message(signable)
        signature = signed.signature.hex()

        async with self.session.post(
            f"{API_URL}/auth/login",
            json={"message": message, "signature": f"0x{signature}"}
        ) as resp:
            data = await resp.json()
            self.token = data["token"]
            return data["client"]

    async def upload_scan_data(self, scan_id: int, scan_type: str, indication: str) -> str:
        """Upload simulated MRI scan metadata to IPFS"""
        headers = {"Authorization": f"Bearer {self.token}"}

        # Generate realistic scan metadata
        scan_data = {
            "type": "mri_scan",
            "scan_id": f"SPINE-{scan_id:04d}",
            "modality": "MRI",
            "body_part": scan_type,
            "clinical_indication": indication,
            "patient_id": f"PT-{random.randint(10000, 99999)}",
            "study_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "series": [
                {"name": "T1_SAG", "slices": random.randint(15, 25)},
                {"name": "T2_SAG", "slices": random.randint(15, 25)},
                {"name": "T2_AX", "slices": random.randint(20, 40)},
                {"name": "STIR", "slices": random.randint(15, 25)}
            ],
            "field_strength": "3.0T",
            "manufacturer": random.choice(["Siemens", "GE", "Philips"]),
            "protocol": f"spine_{scan_type}_standard"
        }

        # Upload as JSON (simulating DICOM metadata)
        scan_bytes = json.dumps(scan_data).encode()

        form = aiohttp.FormData()
        form.add_field(
            'file',
            scan_bytes,
            filename=f'scan_{scan_id:04d}.json',
            content_type='application/json'
        )

        async with self.session.post(
            f"{API_URL}/upload/file",
            headers=headers,
            data=form
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Upload failed: {await resp.text()}")
            data = await resp.json()
            return data["cid"]

    async def submit_job(self, scan_id: int, input_cid: str, scan_type: str) -> dict:
        """Submit inference job"""
        headers = {"Authorization": f"Bearer {self.token}"}

        job_request = {
            "input_cid": input_cid,
            "model": "spineseg-v2",  # Spinal segmentation model
            "name": f"Spinal MRI #{scan_id:04d} - {scan_type}"
        }

        async with self.session.post(
            f"{API_URL}/jobs/submit",
            headers=headers,
            json=job_request
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Submit failed: {await resp.text()}")
            return await resp.json()

    async def submit_batch(self, count: int = 100):
        """Submit batch of jobs"""
        print()
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║  SWARMPOOL PROTOCOL TEST — 100 SPINAL MRI ORDERS                 ║")
        print("╠══════════════════════════════════════════════════════════════════╣")
        print("║  Client: dev.clientswarm.eth                                     ║")
        print("║  Worker: bumble70b.swarmpool.eth                                 ║")
        print("║  Model:  spineseg-v2                                             ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print()

        async with aiohttp.ClientSession() as session:
            self.session = session

            # Login
            print("Authenticating...")
            client = await self.login()
            print(f"  ✓ Logged in as {client.get('ens', client['wallet'])}")
            print(f"  ✓ Balance: ${client['balance']:.2f}")
            print(f"  ✓ Free scans: {client['free_scans_remaining']}")
            print()

            print("═" * 64)
            print("SUBMITTING 100 SPINAL MRI SCAN ORDERS")
            print("═" * 64)
            print()

            start_time = datetime.now()

            for i in range(1, count + 1):
                scan_type = random.choice(SCAN_TYPES)
                indication = random.choice(CLINICAL_INDICATIONS)

                try:
                    # Upload scan data
                    input_cid = await self.upload_scan_data(i, scan_type, indication)

                    # Submit job
                    job = await self.submit_job(i, input_cid, scan_type)

                    self.jobs_submitted.append({
                        "scan_id": i,
                        "job_id": job["job_id"],
                        "scan_type": scan_type,
                        "indication": indication,
                        "input_cid": input_cid
                    })

                    # Progress indicator
                    if i % 10 == 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        rate = i / elapsed
                        print(f"  [{i:3d}/100] ████████████████████ {rate:.1f} jobs/sec")
                    elif i % 5 == 0:
                        print(f"  [{i:3d}/100] ██████████")

                except Exception as e:
                    print(f"  [{i:3d}/100] ✗ Error: {e}")

            elapsed = (datetime.now() - start_time).total_seconds()

            print()
            print("═" * 64)
            print(f"BATCH COMPLETE: {len(self.jobs_submitted)} jobs submitted")
            print(f"Time: {elapsed:.1f}s ({len(self.jobs_submitted)/elapsed:.1f} jobs/sec)")
            print("═" * 64)
            print()

            # Save job IDs for tracking
            with open("/tmp/batch_jobs.json", "w") as f:
                json.dump(self.jobs_submitted, f, indent=2)

            print("Job IDs saved to /tmp/batch_jobs.json")
            print()
            print("Run worker to process:")
            print("  python scripts/worker_bumble70b.py")

            return self.jobs_submitted


async def main():
    test = ProtocolTest()
    await test.submit_batch(100)


if __name__ == "__main__":
    asyncio.run(main())
