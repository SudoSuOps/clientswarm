#!/usr/bin/env python3
"""
Setup Test Client: dev.clientswarm.eth
Fund with $1000 balance
"""
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from eth_account import Account

# Test client wallet - deterministic for dev
# Using Anvil's first test account
DEV_WALLET = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
DEV_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

MONGODB_URL = "mongodb://localhost:27017"
MONGODB_DB = "clientswarm"


async def setup_test_client():
    """Create or update dev.clientswarm.eth test client"""

    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB]

    # Create indexes if needed
    await db.clients.create_index("wallet", unique=True)
    await db.clients.create_index("ens")

    wallet = DEV_WALLET.lower()
    ens = "dev.clientswarm.eth"

    # Check if exists
    existing = await db.clients.find_one({"wallet": wallet})

    if existing:
        # Update balance to $1000
        result = await db.clients.update_one(
            {"wallet": wallet},
            {"$set": {
                "balance": 1000.0,
                "ens": ens,
                "free_scans_remaining": 10
            }}
        )
        print(f"✓ Updated existing client")
    else:
        # Create new
        test_client = {
            "wallet": wallet,
            "ens": ens,
            "created_at": datetime.utcnow(),
            "balance": 1000.0,  # $1000 funded
            "free_scans_remaining": 10,
            "total_jobs": 0,
            "settings": {
                "notifications": True,
                "auto_download": False
            }
        }
        await db.clients.insert_one(test_client)
        print(f"✓ Created new test client")

    # Verify
    client_doc = await db.clients.find_one({"wallet": wallet})

    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  TEST CLIENT: dev.clientswarm.eth                                ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Wallet:  {wallet}  ║")
    print(f"║  ENS:     {ens:<43}  ║")
    print(f"║  Balance: ${client_doc['balance']:<42.2f}  ║")
    print(f"║  Free:    {client_doc['free_scans_remaining']} scans remaining{' ' * 30}  ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print("║  Private Key (Anvil #0 - DEV ONLY):                              ║")
    print(f"║  {DEV_PRIVATE_KEY}  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    client.close()


if __name__ == "__main__":
    asyncio.run(setup_test_client())
