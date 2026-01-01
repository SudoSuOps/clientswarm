"""
Settings API - Profile, Billing, API Keys
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from api.auth import get_current_client
from services.database import get_clients_collection
from services.crypto import generate_nonce
from config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])
settings = get_settings()


class ProfileUpdate(BaseModel):
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    notify_on_complete: Optional[bool] = None


class BalanceResponse(BaseModel):
    balance: float
    free_scans_remaining: int
    price_per_scan: float


class AddFundsRequest(BaseModel):
    amount: float
    payment_method: str  # "stripe" or "usdc"


class ApiKeyResponse(BaseModel):
    key: str
    created_at: datetime
    last_used: Optional[datetime]


@router.get("/profile")
async def get_profile(client: dict = Depends(get_current_client)):
    """Get client profile"""
    return {
        "wallet": client["wallet"],
        "ens": client.get("ens"),
        "email": client.get("settings", {}).get("email"),
        "webhook_url": client.get("settings", {}).get("webhook_url"),
        "notify_on_complete": client.get("settings", {}).get("notify_on_complete", True),
        "created_at": client.get("created_at"),
        "total_jobs": client.get("total_jobs", 0)
    }


@router.patch("/profile")
async def update_profile(
    update: ProfileUpdate,
    client: dict = Depends(get_current_client)
):
    """Update client profile settings"""
    clients = get_clients_collection()

    update_data = {}
    if update.webhook_url is not None:
        update_data["settings.webhook_url"] = update.webhook_url
    if update.email is not None:
        update_data["settings.email"] = update.email
    if update.notify_on_complete is not None:
        update_data["settings.notify_on_complete"] = update.notify_on_complete

    if update_data:
        await clients.update_one(
            {"wallet": client["wallet"]},
            {"$set": update_data}
        )

    return {"status": "updated"}


@router.get("/billing", response_model=BalanceResponse)
async def get_billing(client: dict = Depends(get_current_client)):
    """Get billing information"""
    return {
        "balance": client.get("balance", 0.0),
        "free_scans_remaining": client.get("free_scans_remaining", 0),
        "price_per_scan": settings.price_per_scan
    }


@router.post("/billing/add-funds")
async def add_funds(
    request: AddFundsRequest,
    client: dict = Depends(get_current_client)
):
    """
    Add funds to account.

    In production: integrate with Stripe or USDC payment.
    """
    if request.amount <= 0:
        raise HTTPException(400, "Amount must be positive")

    if request.amount > 1000:
        raise HTTPException(400, "Max deposit: $1000")

    # In production: process payment via Stripe or verify USDC transfer
    # For now: just credit the balance (demo mode)

    clients = get_clients_collection()
    await clients.update_one(
        {"wallet": client["wallet"]},
        {"$inc": {"balance": request.amount}}
    )

    return {
        "status": "credited",
        "amount": request.amount,
        "new_balance": client.get("balance", 0) + request.amount
    }


@router.post("/api-keys/generate", response_model=ApiKeyResponse)
async def generate_api_key(client: dict = Depends(get_current_client)):
    """Generate a new API key for programmatic access"""
    key = f"cs_{generate_nonce()}"

    clients = get_clients_collection()
    await clients.update_one(
        {"wallet": client["wallet"]},
        {
            "$push": {
                "api_keys": {
                    "key": key,
                    "created_at": datetime.utcnow(),
                    "last_used": None
                }
            }
        }
    )

    return {
        "key": key,
        "created_at": datetime.utcnow(),
        "last_used": None
    }


@router.get("/api-keys")
async def list_api_keys(client: dict = Depends(get_current_client)):
    """List API keys (masked)"""
    keys = client.get("api_keys", [])
    return [
        {
            "key": f"{k['key'][:8]}...{k['key'][-4:]}",
            "created_at": k["created_at"],
            "last_used": k.get("last_used")
        }
        for k in keys
    ]


@router.delete("/api-keys/{key_prefix}")
async def revoke_api_key(
    key_prefix: str,
    client: dict = Depends(get_current_client)
):
    """Revoke an API key"""
    clients = get_clients_collection()
    await clients.update_one(
        {"wallet": client["wallet"]},
        {
            "$pull": {
                "api_keys": {"key": {"$regex": f"^{key_prefix}"}}
            }
        }
    )

    return {"status": "revoked"}
