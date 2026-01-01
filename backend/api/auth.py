"""
Authentication API - SIWE (Sign-In with Ethereum)
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from siwe import SiweMessage

from config import get_settings
from services.database import get_clients_collection
from services.crypto import generate_nonce

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()
settings = get_settings()


class NonceResponse(BaseModel):
    nonce: str


class LoginRequest(BaseModel):
    message: str
    signature: str


class LoginResponse(BaseModel):
    token: str
    client: dict


class RegisterRequest(BaseModel):
    message: str
    signature: str
    ens_subdomain: str  # e.g., "xyzclinic" -> xyzclinic.clientswarm.eth


class ClientResponse(BaseModel):
    wallet: str
    ens: Optional[str]
    created_at: datetime
    balance: float
    free_scans_remaining: int


# Nonce storage (in production: use Redis)
_nonces: dict = {}


@router.get("/nonce", response_model=NonceResponse)
async def get_nonce():
    """Get a nonce for SIWE login"""
    nonce = generate_nonce()
    _nonces[nonce] = datetime.utcnow()
    return {"nonce": nonce}


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login with Sign-In with Ethereum (SIWE).

    Client signs a message with their wallet, we verify and issue JWT.
    """
    try:
        # Parse SIWE message
        siwe_message = SiweMessage.from_message(request.message)

        # Verify nonce
        if siwe_message.nonce not in _nonces:
            raise HTTPException(400, "Invalid or expired nonce")

        # Verify signature
        siwe_message.verify(request.signature)

        # Remove used nonce
        del _nonces[siwe_message.nonce]

        wallet = siwe_message.address.lower()

    except Exception as e:
        raise HTTPException(400, f"Invalid signature: {str(e)}")

    # Get or create client
    clients = get_clients_collection()
    client = await clients.find_one({"wallet": wallet})

    if not client:
        # New client - create with free trial
        client = {
            "wallet": wallet,
            "ens": None,
            "created_at": datetime.utcnow(),
            "balance": 0.0,
            "free_scans_remaining": settings.free_trial_scans,
            "total_jobs": 0,
            "settings": {}
        }
        await clients.insert_one(client)

    # Generate JWT
    token = create_token(wallet)

    # Clean response
    client["_id"] = str(client["_id"])

    return {"token": token, "client": client}


@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """
    Register with ENS subdomain.

    Creates xyzclinic.clientswarm.eth identity.
    """
    try:
        # Parse and verify SIWE
        siwe_message = SiweMessage.from_message(request.message)

        if siwe_message.nonce not in _nonces:
            raise HTTPException(400, "Invalid or expired nonce")

        siwe_message.verify(request.signature)
        del _nonces[siwe_message.nonce]

        wallet = siwe_message.address.lower()

    except Exception as e:
        raise HTTPException(400, f"Invalid signature: {str(e)}")

    # Validate subdomain
    subdomain = request.ens_subdomain.lower().strip()
    if not subdomain.isalnum() or len(subdomain) < 3:
        raise HTTPException(400, "Invalid subdomain. Use alphanumeric, min 3 chars.")

    ens = f"{subdomain}.clientswarm.eth"

    # Check if ENS already taken
    clients = get_clients_collection()
    existing = await clients.find_one({"ens": ens})
    if existing:
        raise HTTPException(400, f"ENS {ens} already registered")

    # Check if wallet already registered
    client = await clients.find_one({"wallet": wallet})

    if client:
        # Update existing client with ENS
        await clients.update_one(
            {"wallet": wallet},
            {"$set": {"ens": ens}}
        )
        client["ens"] = ens
    else:
        # Create new client
        client = {
            "wallet": wallet,
            "ens": ens,
            "created_at": datetime.utcnow(),
            "balance": 0.0,
            "free_scans_remaining": settings.free_trial_scans,
            "total_jobs": 0,
            "settings": {}
        }
        await clients.insert_one(client)

    token = create_token(wallet)
    client["_id"] = str(client["_id"])

    return {"token": token, "client": client}


def create_token(wallet: str) -> str:
    """Create JWT token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": wallet,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated client"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        wallet = payload.get("sub")
        if not wallet:
            raise HTTPException(401, "Invalid token")

    except JWTError:
        raise HTTPException(401, "Invalid token")

    clients = get_clients_collection()
    client = await clients.find_one({"wallet": wallet})

    if not client:
        raise HTTPException(401, "Client not found")

    client["_id"] = str(client["_id"])
    return client


@router.get("/me", response_model=ClientResponse)
async def get_me(client: dict = Depends(get_current_client)):
    """Get current client info"""
    return client
