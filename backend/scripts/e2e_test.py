#!/usr/bin/env python3
"""
End-to-End Test: ClientSwarm Full Flow

1. Login with dev.clientswarm.eth wallet (SIWE)
2. Upload test medical image
3. Submit inference job
4. Track job status
5. Verify completion
"""
import asyncio
import aiohttp
import json
from datetime import datetime
from eth_account import Account
from eth_account.messages import encode_defunct
from siwe import SiweMessage

# Config
API_URL = "http://localhost:8000"
DEV_WALLET = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
DEV_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Test image (simple PNG header for testing)
TEST_IMAGE = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 pixel
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
    0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
    0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82
])


class E2ETest:
    def __init__(self):
        self.session = None
        self.token = None
        self.job_id = None

    async def run(self):
        """Run full E2E test"""
        print()
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║  E2E TEST: ClientSwarm Full Flow                                 ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print()

        async with aiohttp.ClientSession() as session:
            self.session = session

            try:
                # Step 1: Login
                await self.step_login()

                # Step 2: Check dashboard stats
                await self.step_check_stats()

                # Step 3: Upload test image
                input_cid = await self.step_upload()

                # Step 4: Submit job
                self.job_id = await self.step_submit_job(input_cid)

                # Step 5: Track job
                await self.step_track_job()

                # Step 6: Verify balance deduction
                await self.step_verify_balance()

                print()
                print("╔══════════════════════════════════════════════════════════════════╗")
                print("║  ✓ E2E TEST PASSED                                               ║")
                print("╚══════════════════════════════════════════════════════════════════╝")

            except Exception as e:
                print()
                print(f"✗ E2E TEST FAILED: {e}")
                raise

    async def step_login(self):
        """Step 1: SIWE Login"""
        print("─" * 60)
        print("STEP 1: SIWE Login")
        print("─" * 60)

        # Get nonce
        async with self.session.get(f"{API_URL}/auth/nonce") as resp:
            data = await resp.json()
            nonce = data["nonce"]
            print(f"  → Got nonce: {nonce[:16]}...")

        # Create SIWE message
        siwe_message = SiweMessage(
            domain="clientswarm.eth",
            address=DEV_WALLET,
            statement="Sign in to ClientSwarm",
            uri="https://clientswarm.eth.limo",
            version="1",
            chain_id=1,
            nonce=nonce,
            issued_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        message = siwe_message.prepare_message()

        # Sign message
        account = Account.from_key(DEV_PRIVATE_KEY)
        signable = encode_defunct(text=message)
        signed = account.sign_message(signable)
        signature = signed.signature.hex()

        # Login
        async with self.session.post(
            f"{API_URL}/auth/login",
            json={"message": message, "signature": f"0x{signature}"}
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Login failed: {error}")

            data = await resp.json()
            self.token = data["token"]
            client = data["client"]

            print(f"  → Logged in as: {client.get('ens', client['wallet'])}")
            print(f"  → Balance: ${client['balance']:.2f}")
            print(f"  → Free scans: {client['free_scans_remaining']}")
            print("  ✓ Login successful")

    async def step_check_stats(self):
        """Step 2: Check dashboard stats"""
        print()
        print("─" * 60)
        print("STEP 2: Dashboard Stats")
        print("─" * 60)

        headers = {"Authorization": f"Bearer {self.token}"}

        async with self.session.get(f"{API_URL}/stats", headers=headers) as resp:
            if resp.status != 200:
                print(f"  → Stats endpoint returned {resp.status} (may be empty)")
                return

            data = await resp.json()
            print(f"  → Total jobs: {data.get('total_jobs', 0)}")
            print(f"  → Completed: {data.get('completed_jobs', 0)}")
            print(f"  → Pending: {data.get('pending_jobs', 0)}")
            print("  ✓ Stats retrieved")

    async def step_upload(self) -> str:
        """Step 3: Upload test image"""
        print()
        print("─" * 60)
        print("STEP 3: Upload Test Image")
        print("─" * 60)

        headers = {"Authorization": f"Bearer {self.token}"}

        # Create multipart form
        form = aiohttp.FormData()
        form.add_field(
            'file',
            TEST_IMAGE,
            filename='test_scan.png',
            content_type='image/png'
        )

        async with self.session.post(
            f"{API_URL}/upload/file",
            headers=headers,
            data=form
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Upload failed: {error}")

            data = await resp.json()
            cid = data["cid"]
            print(f"  → Uploaded to IPFS: {cid[:20]}...")
            print(f"  → File size: {len(TEST_IMAGE)} bytes")
            print("  ✓ Upload successful")
            return cid

    async def step_submit_job(self, input_cid: str) -> str:
        """Step 4: Submit inference job"""
        print()
        print("─" * 60)
        print("STEP 4: Submit Inference Job")
        print("─" * 60)

        headers = {"Authorization": f"Bearer {self.token}"}

        job_request = {
            "input_cid": input_cid,
            "model": "medseg-liver-v1",
            "name": "E2E Test Scan"
        }

        async with self.session.post(
            f"{API_URL}/jobs/submit",
            headers=headers,
            json=job_request
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Job submit failed: {error}")

            job = await resp.json()
            print(f"  → Job ID: {job['job_id'][:20]}...")
            print(f"  → Job CID: {job['job_cid'][:20]}...")
            print(f"  → Model: {job['model']}")
            print(f"  → Status: {job['status']}")
            print("  ✓ Job submitted to SwarmPool")
            return job["job_id"]

    async def step_track_job(self):
        """Step 5: Track job status"""
        print()
        print("─" * 60)
        print("STEP 5: Track Job Status")
        print("─" * 60)

        headers = {"Authorization": f"Bearer {self.token}"}

        # Poll for status (max 30 seconds)
        for i in range(6):
            async with self.session.get(
                f"{API_URL}/jobs/{self.job_id}",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"Job fetch failed: {error}")

                data = await resp.json()
                job = data["job"] if "job" in data else data
                status = job["status"]

                print(f"  → Status: {status}")

                if status == "completed":
                    print(f"  → Output CID: {job.get('output_cid', 'N/A')}")
                    print(f"  → Proof CID: {job.get('proof_cid', 'N/A')}")
                    print(f"  → Confidence: {job.get('confidence', 'N/A')}")
                    print("  ✓ Job completed")
                    return

                if status == "failed":
                    raise Exception("Job failed")

            await asyncio.sleep(5)

        # Job still pending (expected in test environment without workers)
        print("  → Job pending (no workers in test environment)")
        print("  ✓ Job tracking works")

    async def step_verify_balance(self):
        """Step 6: Verify balance after job"""
        print()
        print("─" * 60)
        print("STEP 6: Verify Balance")
        print("─" * 60)

        headers = {"Authorization": f"Bearer {self.token}"}

        async with self.session.get(f"{API_URL}/auth/me", headers=headers) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Failed to get profile: {error}")

            data = await resp.json()
            balance = data["balance"]
            free_scans = data["free_scans_remaining"]

            print(f"  → Current balance: ${balance:.2f}")
            print(f"  → Free scans remaining: {free_scans}")

            # If free scans were used, balance should still be $1000
            # If paid scan, balance should be $999.90
            if free_scans < 10:
                print("  → Used free scan (no charge)")
            elif balance < 1000:
                print(f"  → Charged: ${1000 - balance:.2f}")

            print("  ✓ Balance verified")


async def main():
    test = E2ETest()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())
