"""
Cryptographic utilities for ClientSwarm
"""
import json
import hashlib
from typing import Any, Dict
from eth_account import Account
from eth_account.messages import encode_defunct


def keccak256(data: bytes) -> str:
    """Compute keccak256 hash"""
    from web3 import Web3
    return Web3.keccak(data).hex()


def sign_message(message: str, private_key: str) -> str:
    """Sign a message with EIP-191"""
    account = Account.from_key(private_key)
    message_hash = encode_defunct(text=message)
    signed = account.sign_message(message_hash)
    return signed.signature.hex()


def sign_snapshot(data: Dict[str, Any], private_key: str) -> str:
    """Sign a snapshot (canonical JSON)"""
    # Remove existing sig if present
    data_copy = {k: v for k, v in data.items() if k != "sig"}

    # Canonical JSON
    canonical = json.dumps(data_copy, separators=(",", ":"), sort_keys=True)

    # Hash and sign
    message_hash = keccak256(canonical.encode())
    return sign_message(message_hash, private_key)


def verify_signature(message: str, signature: str, expected_address: str) -> bool:
    """Verify an EIP-191 signature"""
    try:
        message_hash = encode_defunct(text=message)
        recovered = Account.recover_message(message_hash, signature=signature)
        return recovered.lower() == expected_address.lower()
    except Exception:
        return False


def generate_job_id() -> str:
    """Generate unique job ID"""
    import time
    import secrets
    timestamp = time.strftime("%Y%m%d%H%M%S")
    nonce = secrets.token_hex(4)
    return f"job-{timestamp}-{nonce}"


def generate_nonce() -> str:
    """Generate random nonce"""
    import secrets
    return secrets.token_hex(16)
