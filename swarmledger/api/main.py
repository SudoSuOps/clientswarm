"""
SwarmLedger API

The settlement layer for SwarmOS.

Responsibilities:
- Balance management (clients + workers)
- Deposit tracking
- Epoch settlement
- Payout processing
- Transaction history
"""

import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =============================================================================
# Configuration
# =============================================================================

class Config:
    HOST: str = os.getenv("LEDGER_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("LEDGER_PORT", "8100"))
    ENS: str = "swarmledger.eth"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ledger.db")
    
    # USDC vault address (receives deposits)
    VAULT_ADDRESS: str = os.getenv("VAULT_ADDRESS", "0x...")
    
    # Fee structure
    WORK_POOL_PCT: int = 70
    READINESS_POOL_PCT: int = 30
    PROTOCOL_FEE_PCT: int = 2
    OPERATOR_FEE_PCT: int = 5
    
    VERSION: str = "1.0.0"


config = Config()


# =============================================================================
# Models
# =============================================================================

class Account(BaseModel):
    ens: str
    account_type: str  # client, worker, treasury
    balance_usd: Decimal = Decimal("0")
    reserved_usd: Decimal = Decimal("0")
    pending_usd: Decimal = Decimal("0")
    total_in_usd: Decimal = Decimal("0")
    total_out_usd: Decimal = Decimal("0")


class Transaction(BaseModel):
    id: str
    account_ens: str
    tx_type: str  # DEPOSIT, JOB_CHARGE, EARNING, PAYOUT, REFUND
    amount_usd: Decimal
    balance_after: Decimal
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    eth_tx_hash: Optional[str] = None
    created_at: datetime


# =============================================================================
# Request/Response Schemas
# =============================================================================

class BalanceResponse(BaseModel):
    ens: str
    account_type: str
    balance_usd: str
    reserved_usd: str
    pending_usd: str
    available_usd: str
    total_in_usd: str
    total_out_usd: str


class ReserveFundsRequest(BaseModel):
    amount_usd: str
    job_id: str


class ChargeFundsRequest(BaseModel):
    amount_usd: str
    job_id: str


class CreditEarningsRequest(BaseModel):
    amount_usd: str
    job_id: str
    pending: bool = True


class DepositRequest(BaseModel):
    client_ens: str
    amount_usd: str
    eth_tx_hash: str


class WithdrawalRequest(BaseModel):
    worker_ens: str
    amount_usd: str
    destination_address: str
    signature: str


class EpochSealRequest(BaseModel):
    epoch_id: str
    jobs_merkle_root: str
    jobs_count: int
    total_revenue_usd: str
    settlements: list[dict]
    signature: str


class TransactionHistoryResponse(BaseModel):
    account_ens: str
    transactions: list[dict]
    total_count: int


# =============================================================================
# In-Memory Store (Would be DB in production)
# =============================================================================

class LedgerStore:
    def __init__(self):
        self.accounts: dict[str, dict] = {}
        self.transactions: list[dict] = []
        self.deposits: list[dict] = []
        self.withdrawals: list[dict] = []
        self.epochs: dict[str, dict] = {}
        self.tx_counter = 0
        
        # Initialize treasury accounts
        self._init_account("swarmbank.eth", "treasury")
        self._init_account("bee23.eth", "treasury")  # Protocol
        self._init_account("swarmos.eth", "treasury")  # Operator
        
        # Demo data
        self._init_account("xyzclinic.clientswarm.eth", "client", balance=Decimal("245.00"))
        self._init_account("acme.clientswarm.eth", "client", balance=Decimal("1240.00"))
        self._init_account("bee-01.swarmbee.eth", "worker", balance=Decimal("847.30"))
        self._init_account("bee-02.swarmbee.eth", "worker", balance=Decimal("623.15"))
        
        # Demo epochs
        self.epochs["epoch-001"] = {
            "id": "epoch-001",
            "status": "finalized",
            "jobs_count": 105,
            "jobs_merkle_root": "7ec20e03b05b7898c3cdc33f0d066ddf860091338eaace5ad51df1f1f8c472b5",
            "total_revenue_usd": "10.50",
            "sealed_at": "2025-01-16T00:00:00Z",
        }
        self.epochs["epoch-002"] = {
            "id": "epoch-002",
            "status": "finalized",
            "jobs_count": 248,
            "jobs_merkle_root": "a3f891c2e7d4b5f6a8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1",
            "total_revenue_usd": "24.80",
            "sealed_at": "2025-01-17T00:00:00Z",
        }
        self.epochs["epoch-003"] = {
            "id": "epoch-003",
            "status": "active",
            "jobs_count": 67,
            "jobs_merkle_root": None,
            "total_revenue_usd": "6.70",
            "sealed_at": None,
        }
    
    def _init_account(
        self,
        ens: str,
        account_type: str,
        balance: Decimal = Decimal("0")
    ):
        self.accounts[ens] = {
            "ens": ens,
            "account_type": account_type,
            "balance_usd": balance,
            "reserved_usd": Decimal("0"),
            "pending_usd": Decimal("0"),
            "total_in_usd": balance,
            "total_out_usd": Decimal("0"),
        }
    
    def get_account(self, ens: str) -> Optional[dict]:
        return self.accounts.get(ens)
    
    def get_or_create_account(self, ens: str, account_type: str) -> dict:
        if ens not in self.accounts:
            self._init_account(ens, account_type)
        return self.accounts[ens]
    
    def record_transaction(
        self,
        account_ens: str,
        tx_type: str,
        amount: Decimal,
        balance_after: Decimal,
        reference_type: str = None,
        reference_id: str = None,
        eth_tx_hash: str = None,
    ) -> str:
        self.tx_counter += 1
        tx_id = f"tx-{self.tx_counter:05d}"
        
        self.transactions.append({
            "id": tx_id,
            "account_ens": account_ens,
            "tx_type": tx_type,
            "amount_usd": str(amount),
            "balance_after": str(balance_after),
            "reference_type": reference_type,
            "reference_id": reference_id,
            "eth_tx_hash": eth_tx_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        
        return tx_id
    
    def get_transactions(self, account_ens: str, limit: int = 50) -> list[dict]:
        return [
            tx for tx in reversed(self.transactions)
            if tx["account_ens"] == account_ens
        ][:limit]


store = LedgerStore()


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"💰 SwarmLedger API starting...")
    print(f"   ENS: {config.ENS}")
    print(f"   Vault: {config.VAULT_ADDRESS}")
    yield
    print(f"💰 SwarmLedger API shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="SwarmLedger API",
    description="Settlement layer for SwarmOS",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://swarmledger.eth.limo",
        "https://swarmorb.eth.limo",
        "https://swarmos.eth.limo",
        "https://clientswarm.eth.limo",
        "http://localhost:3000",
        "http://localhost:4321",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "swarmledger",
        "version": config.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/stats")
async def get_stats():
    """Get ledger-wide statistics."""
    total_client_balance = sum(
        a["balance_usd"] for a in store.accounts.values()
        if a["account_type"] == "client"
    )
    total_worker_balance = sum(
        a["balance_usd"] for a in store.accounts.values()
        if a["account_type"] == "worker"
    )
    
    return {
        "total_accounts": len(store.accounts),
        "total_client_balance_usd": str(total_client_balance),
        "total_worker_balance_usd": str(total_worker_balance),
        "total_transactions": len(store.transactions),
        "epochs_finalized": sum(1 for e in store.epochs.values() if e["status"] == "finalized"),
        "current_epoch": "epoch-003",
    }


# =============================================================================
# Balances
# =============================================================================

@app.get("/v1/balances/{ens}", response_model=BalanceResponse)
async def get_balance(ens: str):
    """Get account balance."""
    account = store.get_account(ens)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    balance = account["balance_usd"]
    reserved = account["reserved_usd"]
    pending = account["pending_usd"]
    
    # Available = balance - reserved (for clients)
    # Available = balance (for workers, pending is separate)
    if account["account_type"] == "client":
        available = balance - reserved
    else:
        available = balance
    
    return BalanceResponse(
        ens=ens,
        account_type=account["account_type"],
        balance_usd=str(balance),
        reserved_usd=str(reserved),
        pending_usd=str(pending),
        available_usd=str(available),
        total_in_usd=str(account["total_in_usd"]),
        total_out_usd=str(account["total_out_usd"]),
    )


@app.post("/v1/balances/{ens}/reserve")
async def reserve_funds(ens: str, request: ReserveFundsRequest):
    """Reserve funds for a pending job."""
    account = store.get_account(ens)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    amount = Decimal(request.amount_usd)
    available = account["balance_usd"] - account["reserved_usd"]
    
    if available < amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient funds. Available: ${available}, Required: ${amount}"
        )
    
    account["reserved_usd"] += amount
    
    return {
        "status": "reserved",
        "amount_usd": str(amount),
        "job_id": request.job_id,
        "reserved_total": str(account["reserved_usd"]),
    }


@app.post("/v1/balances/{ens}/charge")
async def charge_funds(ens: str, request: ChargeFundsRequest):
    """Finalize charge after job completion (moves from reserved to spent)."""
    account = store.get_account(ens)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    amount = Decimal(request.amount_usd)
    
    if account["reserved_usd"] < amount:
        raise HTTPException(status_code=400, detail="Charge exceeds reserved amount")
    
    account["reserved_usd"] -= amount
    account["balance_usd"] -= amount
    account["total_out_usd"] += amount
    
    # Record transaction
    tx_id = store.record_transaction(
        account_ens=ens,
        tx_type="JOB_CHARGE",
        amount=-amount,
        balance_after=account["balance_usd"],
        reference_type="job",
        reference_id=request.job_id,
    )
    
    return {
        "status": "charged",
        "amount_usd": str(amount),
        "job_id": request.job_id,
        "new_balance": str(account["balance_usd"]),
        "transaction_id": tx_id,
    }


@app.post("/v1/balances/{ens}/credit")
async def credit_earnings(ens: str, request: CreditEarningsRequest):
    """Credit worker earnings."""
    account = store.get_or_create_account(ens, "worker")
    
    amount = Decimal(request.amount_usd)
    
    if request.pending:
        # Add to pending (will be finalized at epoch settlement)
        account["pending_usd"] += amount
    else:
        # Add directly to available balance
        account["balance_usd"] += amount
        account["total_in_usd"] += amount
        
        # Record transaction
        store.record_transaction(
            account_ens=ens,
            tx_type="EARNING",
            amount=amount,
            balance_after=account["balance_usd"],
            reference_type="job",
            reference_id=request.job_id,
        )
    
    return {
        "status": "credited",
        "amount_usd": str(amount),
        "pending": request.pending,
        "job_id": request.job_id,
    }


# =============================================================================
# Deposits
# =============================================================================

@app.post("/v1/deposits")
async def record_deposit(request: DepositRequest):
    """Record a USDC deposit from L1."""
    account = store.get_or_create_account(request.client_ens, "client")
    
    amount = Decimal(request.amount_usd)
    
    # Credit balance
    account["balance_usd"] += amount
    account["total_in_usd"] += amount
    
    # Record deposit
    store.deposits.append({
        "id": f"dep-{len(store.deposits)+1:05d}",
        "client_ens": request.client_ens,
        "amount_usd": str(amount),
        "eth_tx_hash": request.eth_tx_hash,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    
    # Record transaction
    tx_id = store.record_transaction(
        account_ens=request.client_ens,
        tx_type="DEPOSIT",
        amount=amount,
        balance_after=account["balance_usd"],
        reference_type="eth_tx",
        reference_id=request.eth_tx_hash,
        eth_tx_hash=request.eth_tx_hash,
    )
    
    return {
        "status": "confirmed",
        "client_ens": request.client_ens,
        "amount_usd": str(amount),
        "new_balance": str(account["balance_usd"]),
        "scans_available": int(account["balance_usd"] / Decimal("0.10")),
        "transaction_id": tx_id,
    }


@app.get("/v1/deposits")
async def list_deposits(client_ens: Optional[str] = None, limit: int = 50):
    """List deposits."""
    deposits = store.deposits
    if client_ens:
        deposits = [d for d in deposits if d["client_ens"] == client_ens]
    return {"deposits": deposits[:limit], "total": len(deposits)}


# =============================================================================
# Withdrawals
# =============================================================================

@app.post("/v1/withdrawals")
async def request_withdrawal(request: WithdrawalRequest):
    """Request a withdrawal (worker payout)."""
    account = store.get_account(request.worker_ens)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account["account_type"] != "worker":
        raise HTTPException(status_code=400, detail="Only workers can withdraw")
    
    amount = Decimal(request.amount_usd)
    
    if account["balance_usd"] < amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient funds. Available: ${account['balance_usd']}"
        )
    
    # Create withdrawal request
    withdrawal_id = f"wd-{len(store.withdrawals)+1:05d}"
    store.withdrawals.append({
        "id": withdrawal_id,
        "worker_ens": request.worker_ens,
        "amount_usd": str(amount),
        "destination_address": request.destination_address,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    
    # Reserve funds (don't deduct until processed)
    account["reserved_usd"] += amount
    
    return {
        "status": "pending",
        "withdrawal_id": withdrawal_id,
        "amount_usd": str(amount),
        "destination": request.destination_address,
        "message": "Withdrawal queued for processing",
    }


@app.get("/v1/withdrawals/{withdrawal_id}")
async def get_withdrawal(withdrawal_id: str):
    """Get withdrawal status."""
    for w in store.withdrawals:
        if w["id"] == withdrawal_id:
            return w
    raise HTTPException(status_code=404, detail="Withdrawal not found")


# =============================================================================
# Transactions
# =============================================================================

@app.get("/v1/transactions", response_model=TransactionHistoryResponse)
async def get_transactions(account: str, limit: int = 50):
    """Get transaction history for an account."""
    transactions = store.get_transactions(account, limit)
    
    return TransactionHistoryResponse(
        account_ens=account,
        transactions=transactions,
        total_count=len([t for t in store.transactions if t["account_ens"] == account]),
    )


# =============================================================================
# Epochs
# =============================================================================

@app.get("/v1/epochs")
async def list_epochs():
    """List all epochs."""
    return {
        "epochs": list(store.epochs.values()),
        "total": len(store.epochs),
    }


@app.get("/v1/epochs/current")
async def get_current_epoch():
    """Get current active epoch."""
    for epoch in store.epochs.values():
        if epoch["status"] == "active":
            return epoch
    raise HTTPException(status_code=404, detail="No active epoch")


@app.get("/v1/epochs/{epoch_id}")
async def get_epoch(epoch_id: str):
    """Get epoch details."""
    epoch = store.epochs.get(epoch_id)
    if not epoch:
        raise HTTPException(status_code=404, detail="Epoch not found")
    return epoch


@app.post("/v1/epochs/{epoch_id}/seal")
async def seal_epoch(epoch_id: str, request: EpochSealRequest):
    """Seal an epoch with Merkle root and settlements."""
    epoch = store.epochs.get(epoch_id)
    if not epoch:
        raise HTTPException(status_code=404, detail="Epoch not found")
    
    if epoch["status"] != "active":
        raise HTTPException(status_code=400, detail="Epoch already sealed")
    
    # Update epoch
    epoch["status"] = "finalized"
    epoch["jobs_merkle_root"] = request.jobs_merkle_root
    epoch["jobs_count"] = request.jobs_count
    epoch["total_revenue_usd"] = request.total_revenue_usd
    epoch["signature"] = request.signature
    epoch["sealed_at"] = datetime.now(timezone.utc).isoformat()
    
    # Process settlements (finalize worker earnings)
    for settlement in request.settlements:
        worker_ens = settlement["worker_ens"]
        earned = Decimal(settlement["total_earned_usd"])
        
        account = store.get_account(worker_ens)
        if account:
            # Move from pending to available
            account["pending_usd"] -= earned
            account["balance_usd"] += earned
            account["total_in_usd"] += earned
            
            # Record transaction
            store.record_transaction(
                account_ens=worker_ens,
                tx_type="EARNING",
                amount=earned,
                balance_after=account["balance_usd"],
                reference_type="epoch",
                reference_id=epoch_id,
            )
    
    return {
        "status": "sealed",
        "epoch_id": epoch_id,
        "jobs_merkle_root": request.jobs_merkle_root,
        "jobs_count": request.jobs_count,
        "settlements_processed": len(request.settlements),
    }


# =============================================================================
# Verification
# =============================================================================

@app.post("/v1/verify/receipt")
async def verify_receipt(receipt: dict):
    """Verify a job receipt against epoch Merkle root."""
    epoch_id = receipt.get("epoch_id")
    epoch = store.epochs.get(epoch_id)
    
    if not epoch:
        return {"valid": False, "error": "Epoch not found"}
    
    if not epoch.get("jobs_merkle_root"):
        return {"valid": False, "error": "Epoch not sealed"}
    
    # In production: verify Merkle proof
    # For now, just check epoch exists and is sealed
    
    return {
        "valid": True,
        "epoch_id": epoch_id,
        "epoch_status": epoch["status"],
        "jobs_merkle_root": epoch["jobs_merkle_root"],
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
