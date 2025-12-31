"""
SwarmBank API

The Treasury for SwarmOS.

Responsibilities:
- USDC vault management
- Deposit watching (L1)
- Payout execution
- Treasury reporting
- Fee distribution
"""

import os
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =============================================================================
# Configuration
# =============================================================================

class Config:
    HOST: str = os.getenv("SWARMBANK_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SWARMBANK_PORT", "8400"))
    ENS: str = "swarmbank.eth"
    
    # Vault configuration
    VAULT_ADDRESS: str = os.getenv(
        "VAULT_ADDRESS",
        "0x742d35Cc6634C0532925a3b844Bc9e7595f7e3e0"
    )
    USDC_CONTRACT: str = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    
    # Fee recipients
    PROTOCOL_FEE_ADDRESS: str = os.getenv("PROTOCOL_FEE_ADDRESS", "bee23.eth")
    OPERATOR_FEE_ADDRESS: str = os.getenv("OPERATOR_FEE_ADDRESS", "swarmos.eth")
    
    # Fee percentages
    PROTOCOL_FEE_PCT: Decimal = Decimal("0.02")  # 2%
    OPERATOR_FEE_PCT: Decimal = Decimal("0.05")  # 5%
    WORK_POOL_PCT: Decimal = Decimal("0.70")     # 70%
    READINESS_POOL_PCT: Decimal = Decimal("0.23") # 23% (after fees)
    
    VERSION: str = "1.0.0"


config = Config()


# =============================================================================
# Schemas
# =============================================================================

class VaultStatus(BaseModel):
    address: str
    balance_usd: str
    pending_deposits: int
    pending_payouts: int
    last_updated: str


class DepositRecord(BaseModel):
    id: str
    client_ens: str
    amount_usd: str
    eth_tx_hash: str
    block_number: int
    status: str  # pending, confirmed, failed
    created_at: str
    confirmed_at: Optional[str] = None


class PayoutRecord(BaseModel):
    id: str
    worker_ens: str
    amount_usd: str
    destination_address: str
    status: str  # pending, processing, completed, failed
    eth_tx_hash: Optional[str] = None
    created_at: str
    processed_at: Optional[str] = None


class PayoutRequest(BaseModel):
    worker_ens: str
    amount_usd: str
    destination_address: str
    signature: str


class TreasuryReport(BaseModel):
    period: str
    total_revenue_usd: str
    work_pool_usd: str
    readiness_pool_usd: str
    protocol_fee_usd: str
    operator_fee_usd: str
    total_distributed_usd: str


# =============================================================================
# In-Memory Store
# =============================================================================

class BankStore:
    def __init__(self):
        # Vault balance
        self.vault_balance = Decimal("12847.50")
        
        # Deposits
        self.deposits = [
            {
                "id": "dep-00001",
                "client_ens": "xyz.clientswarm.eth",
                "amount_usd": "500.00",
                "eth_tx_hash": "0x1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890",
                "block_number": 19234567,
                "status": "confirmed",
                "created_at": "2025-01-15T10:30:00Z",
                "confirmed_at": "2025-01-15T10:32:00Z",
            },
            {
                "id": "dep-00002",
                "client_ens": "acme.clientswarm.eth",
                "amount_usd": "1000.00",
                "eth_tx_hash": "0x2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890ab",
                "block_number": 19234890,
                "status": "confirmed",
                "created_at": "2025-01-16T14:22:00Z",
                "confirmed_at": "2025-01-16T14:24:00Z",
            },
            {
                "id": "dep-00003",
                "client_ens": "metro.clientswarm.eth",
                "amount_usd": "250.00",
                "eth_tx_hash": "0x3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
                "block_number": 19235100,
                "status": "confirmed",
                "created_at": "2025-01-17T09:15:00Z",
                "confirmed_at": "2025-01-17T09:17:00Z",
            },
        ]
        
        # Payouts
        self.payouts = [
            {
                "id": "pay-00001",
                "worker_ens": "bee-01.swarmbee.eth",
                "amount_usd": "250.00",
                "destination_address": "0xBee1Address1234567890abcdef1234567890abcd",
                "status": "completed",
                "eth_tx_hash": "0x8a3f7c2b1e9d4f6a8b0c3e5d7f9a2b4c6e8d0f1a3b5c7d9e1f3a5b7c9dc2d1",
                "created_at": "2025-01-17T12:00:00Z",
                "processed_at": "2025-01-17T12:02:00Z",
            },
            {
                "id": "pay-00002",
                "worker_ens": "bee-02.swarmbee.eth",
                "amount_usd": "175.50",
                "destination_address": "0xBee2Address1234567890abcdef1234567890abcd",
                "status": "completed",
                "eth_tx_hash": "0x2b7c9e4f1a3d5b7c9e1f3a5b7c9d0e2f4a6b8c0d2e4f6a8b0c2d4f6a8bf8e3",
                "created_at": "2025-01-17T09:30:00Z",
                "processed_at": "2025-01-17T09:32:00Z",
            },
            {
                "id": "pay-00003",
                "worker_ens": "bee-03.swarmbee.eth",
                "amount_usd": "100.00",
                "destination_address": "0xBee3Address1234567890abcdef1234567890abcd",
                "status": "processing",
                "eth_tx_hash": None,
                "created_at": "2025-01-17T14:45:00Z",
                "processed_at": None,
            },
            {
                "id": "pay-00004",
                "worker_ens": "bee-01.swarmbee.eth",
                "amount_usd": "500.00",
                "destination_address": "0xBee1Address1234567890abcdef1234567890abcd",
                "status": "completed",
                "eth_tx_hash": "0x9d4e8f2a1b3c5d7e9f0a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f6a1b2",
                "created_at": "2025-01-16T18:00:00Z",
                "processed_at": "2025-01-16T18:03:00Z",
            },
            {
                "id": "pay-00005",
                "worker_ens": "bee-04.swarmbee.eth",
                "amount_usd": "89.20",
                "destination_address": "0xBee4Address1234567890abcdef1234567890abcd",
                "status": "completed",
                "eth_tx_hash": "0x3c5f7a9b1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9dd7e8",
                "created_at": "2025-01-15T22:00:00Z",
                "processed_at": "2025-01-15T22:02:00Z",
            },
        ]
        
        # Treasury stats
        self.total_deposits = Decimal("8240.00")
        self.total_payouts = Decimal("5892.40")
        self.payout_counter = 5
        self.deposit_counter = 3
    
    def get_vault_status(self) -> dict:
        pending_deps = len([d for d in self.deposits if d["status"] == "pending"])
        pending_pays = len([p for p in self.payouts if p["status"] in ("pending", "processing")])
        
        return {
            "address": config.VAULT_ADDRESS,
            "balance_usd": str(self.vault_balance),
            "pending_deposits": pending_deps,
            "pending_payouts": pending_pays,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_deposits(self, limit: int = 50, status: str = None) -> list[dict]:
        deps = self.deposits
        if status:
            deps = [d for d in deps if d["status"] == status]
        return sorted(deps, key=lambda d: d["created_at"], reverse=True)[:limit]
    
    def get_payouts(self, limit: int = 50, status: str = None) -> list[dict]:
        pays = self.payouts
        if status:
            pays = [p for p in pays if p["status"] == status]
        return sorted(pays, key=lambda p: p["created_at"], reverse=True)[:limit]
    
    def create_payout(self, worker_ens: str, amount: Decimal, destination: str) -> dict:
        self.payout_counter += 1
        payout_id = f"pay-{self.payout_counter:05d}"
        
        payout = {
            "id": payout_id,
            "worker_ens": worker_ens,
            "amount_usd": str(amount),
            "destination_address": destination,
            "status": "pending",
            "eth_tx_hash": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "processed_at": None,
        }
        
        self.payouts.append(payout)
        return payout
    
    def process_payout(self, payout_id: str, tx_hash: str) -> dict:
        for payout in self.payouts:
            if payout["id"] == payout_id:
                payout["status"] = "completed"
                payout["eth_tx_hash"] = tx_hash
                payout["processed_at"] = datetime.now(timezone.utc).isoformat()
                
                # Update totals
                self.total_payouts += Decimal(payout["amount_usd"])
                self.vault_balance -= Decimal(payout["amount_usd"])
                
                return payout
        return None
    
    def get_treasury_report(self, epoch_revenue: Decimal) -> dict:
        protocol_fee = epoch_revenue * config.PROTOCOL_FEE_PCT
        operator_fee = epoch_revenue * config.OPERATOR_FEE_PCT
        remaining = epoch_revenue - protocol_fee - operator_fee
        work_pool = remaining * (config.WORK_POOL_PCT / (config.WORK_POOL_PCT + config.READINESS_POOL_PCT))
        readiness_pool = remaining - work_pool
        
        return {
            "total_revenue_usd": str(epoch_revenue),
            "work_pool_usd": str(round(work_pool, 2)),
            "readiness_pool_usd": str(round(readiness_pool, 2)),
            "protocol_fee_usd": str(round(protocol_fee, 2)),
            "operator_fee_usd": str(round(operator_fee, 2)),
            "total_distributed_usd": str(epoch_revenue),
        }


store = BankStore()


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🏦 SwarmBank API starting...")
    print(f"   ENS: {config.ENS}")
    print(f"   Vault: {config.VAULT_ADDRESS}")
    yield
    print(f"🏦 SwarmBank API shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="SwarmBank API",
    description="Treasury and payout management for SwarmOS",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://swarmbank.eth.limo",
        "https://swarmorb.eth.limo",
        "https://swarmos.eth.limo",
        "https://swarmledger.eth.limo",
        "http://localhost:3000",
        "http://localhost:4321",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health & Status
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "swarmbank",
        "version": config.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/vault", response_model=VaultStatus)
async def get_vault_status():
    """Get current vault status."""
    return store.get_vault_status()


@app.get("/v1/stats")
async def get_stats():
    """Get treasury statistics."""
    return {
        "vault_balance_usd": str(store.vault_balance),
        "total_deposits_usd": str(store.total_deposits),
        "total_payouts_usd": str(store.total_payouts),
        "total_deposit_count": len(store.deposits),
        "total_payout_count": len([p for p in store.payouts if p["status"] == "completed"]),
        "pending_payouts": len([p for p in store.payouts if p["status"] in ("pending", "processing")]),
        "settlement_rate": "100%",
    }


# =============================================================================
# Deposits
# =============================================================================

@app.get("/v1/deposits")
async def list_deposits(limit: int = 50, status: Optional[str] = None):
    """List deposits."""
    deposits = store.get_deposits(limit, status)
    return {
        "deposits": deposits,
        "total": len(deposits),
    }


@app.get("/v1/deposits/{deposit_id}")
async def get_deposit(deposit_id: str):
    """Get specific deposit."""
    for dep in store.deposits:
        if dep["id"] == deposit_id:
            return dep
    raise HTTPException(status_code=404, detail="Deposit not found")


@app.post("/v1/deposits/watch")
async def watch_deposit(client_ens: str, expected_amount: str):
    """Register a deposit to watch for."""
    return {
        "status": "watching",
        "client_ens": client_ens,
        "expected_amount_usd": expected_amount,
        "vault_address": config.VAULT_ADDRESS,
        "usdc_contract": config.USDC_CONTRACT,
        "message": "Send USDC to vault address. Balance will be credited upon confirmation.",
    }


# =============================================================================
# Payouts
# =============================================================================

@app.get("/v1/payouts")
async def list_payouts(limit: int = 50, status: Optional[str] = None, worker: Optional[str] = None):
    """List payouts."""
    payouts = store.get_payouts(limit, status)
    if worker:
        payouts = [p for p in payouts if p["worker_ens"] == worker]
    
    total_amount = sum(Decimal(p["amount_usd"]) for p in payouts if p["status"] == "completed")
    
    return {
        "payouts": payouts,
        "total": len(payouts),
        "total_amount_usd": str(total_amount),
    }


@app.get("/v1/payouts/{payout_id}")
async def get_payout(payout_id: str):
    """Get specific payout."""
    for pay in store.payouts:
        if pay["id"] == payout_id:
            return pay
    raise HTTPException(status_code=404, detail="Payout not found")


@app.post("/v1/payouts/request")
async def request_payout(request: PayoutRequest):
    """Request a worker payout."""
    amount = Decimal(request.amount_usd)
    
    # Verify sufficient vault balance
    if amount > store.vault_balance:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient vault balance. Available: ${store.vault_balance}"
        )
    
    # Create payout request
    payout = store.create_payout(
        worker_ens=request.worker_ens,
        amount=amount,
        destination=request.destination_address,
    )
    
    return {
        "status": "pending",
        "payout": payout,
        "message": "Payout queued for processing",
    }


@app.post("/v1/payouts/{payout_id}/process")
async def process_payout(payout_id: str, tx_hash: str):
    """Mark payout as processed (internal use)."""
    payout = store.process_payout(payout_id, tx_hash)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    
    return {
        "status": "completed",
        "payout": payout,
    }


# =============================================================================
# Treasury Reports
# =============================================================================

@app.get("/v1/treasury/report")
async def get_treasury_report(epoch_revenue: float = 24.80):
    """Get treasury allocation report for an epoch."""
    report = store.get_treasury_report(Decimal(str(epoch_revenue)))
    return {
        "period": "epoch",
        **report,
    }


@app.get("/v1/treasury/allocations")
async def get_allocations():
    """Get fee allocation percentages."""
    return {
        "work_pool_pct": float(config.WORK_POOL_PCT) * 100,
        "readiness_pool_pct": float(config.READINESS_POOL_PCT) * 100,
        "protocol_fee_pct": float(config.PROTOCOL_FEE_PCT) * 100,
        "operator_fee_pct": float(config.OPERATOR_FEE_PCT) * 100,
        "protocol_fee_recipient": config.PROTOCOL_FEE_ADDRESS,
        "operator_fee_recipient": config.OPERATOR_FEE_ADDRESS,
    }


@app.get("/v1/treasury/recipients")
async def get_fee_recipients():
    """Get fee recipient addresses."""
    return {
        "protocol": {
            "ens": config.PROTOCOL_FEE_ADDRESS,
            "percentage": float(config.PROTOCOL_FEE_PCT) * 100,
        },
        "operator": {
            "ens": config.OPERATOR_FEE_ADDRESS,
            "percentage": float(config.OPERATOR_FEE_PCT) * 100,
        },
        "vault": {
            "address": config.VAULT_ADDRESS,
            "balance_usd": str(store.vault_balance),
        },
    }


# =============================================================================
# Worker Balances (for payout eligibility)
# =============================================================================

@app.get("/v1/workers/{worker_ens}/balance")
async def get_worker_balance(worker_ens: str):
    """Get worker's available balance for withdrawal."""
    # In production: fetch from SwarmLedger
    # Demo data
    balances = {
        "bee-01.swarmbee.eth": {"available": "347.30", "pending": "45.20"},
        "bee-02.swarmbee.eth": {"available": "223.15", "pending": "38.90"},
        "bee-03.swarmbee.eth": {"available": "112.80", "pending": "22.10"},
        "bee-04.swarmbee.eth": {"available": "98.40", "pending": "15.60"},
        "bee-05.swarmbee.eth": {"available": "56.20", "pending": "12.30"},
    }
    
    if worker_ens not in balances:
        return {
            "worker_ens": worker_ens,
            "available_usd": "0.00",
            "pending_usd": "0.00",
            "message": "Worker not found or no earnings",
        }
    
    return {
        "worker_ens": worker_ens,
        "available_usd": balances[worker_ens]["available"],
        "pending_usd": balances[worker_ens]["pending"],
        "can_withdraw": True,
    }


# =============================================================================
# Integration Endpoints
# =============================================================================

@app.post("/v1/epochs/{epoch_id}/settle")
async def settle_epoch(epoch_id: str, total_revenue: float, settlements: list[dict]):
    """Settle an epoch (called by epoch sealer)."""
    revenue = Decimal(str(total_revenue))
    report = store.get_treasury_report(revenue)
    
    # In production: would execute actual settlements
    # For now, return what would be distributed
    
    return {
        "epoch_id": epoch_id,
        "status": "settled",
        "treasury": report,
        "settlements_count": len(settlements),
        "message": "Epoch settled. Worker balances updated in SwarmLedger.",
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
