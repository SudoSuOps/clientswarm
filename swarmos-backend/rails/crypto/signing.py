"""
SwarmOS Rails - Cryptographic Utilities

EIP-191 signing, ENS resolution, Merkle trees.
"""

import hashlib
import json
from typing import Any, Optional
from dataclasses import dataclass

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_typing import ChecksumAddress
from web3 import Web3


# =============================================================================
# EIP-191 Signing & Verification
# =============================================================================

def sign_message(message: str, private_key: str) -> str:
    """
    Sign a message using EIP-191 personal_sign.
    
    Args:
        message: The message to sign
        private_key: Hex-encoded private key (with or without 0x prefix)
    
    Returns:
        Hex-encoded signature
    """
    if not private_key.startswith("0x"):
        private_key = f"0x{private_key}"
    
    message_hash = encode_defunct(text=message)
    signed = Account.sign_message(message_hash, private_key)
    return signed.signature.hex()


def verify_signature(message: str, signature: str, expected_address: str) -> bool:
    """
    Verify an EIP-191 signature.
    
    Args:
        message: The original message
        signature: Hex-encoded signature
        expected_address: Expected signer address (checksummed or not)
    
    Returns:
        True if signature is valid and matches expected address
    """
    try:
        if not signature.startswith("0x"):
            signature = f"0x{signature}"
        
        message_hash = encode_defunct(text=message)
        recovered = Account.recover_message(message_hash, signature=signature)
        
        return recovered.lower() == expected_address.lower()
    except Exception:
        return False


def recover_signer(message: str, signature: str) -> Optional[str]:
    """
    Recover the signer address from a signature.
    
    Returns:
        Checksummed address or None if recovery fails
    """
    try:
        if not signature.startswith("0x"):
            signature = f"0x{signature}"
        
        message_hash = encode_defunct(text=message)
        return Account.recover_message(message_hash, signature=signature)
    except Exception:
        return None


# =============================================================================
# Job Request Signing
# =============================================================================

@dataclass
class SignedJobRequest:
    """A signed job request from a client."""
    job_type: str
    client_ens: str
    dicom_ref: str
    timestamp: int
    nonce: str
    signature: str


def create_job_message(
    job_type: str,
    client_ens: str,
    dicom_ref: str,
    timestamp: int,
    nonce: str
) -> str:
    """Create the canonical message for job signing."""
    return (
        f"SwarmOS Job Request\n"
        f"Type: {job_type}\n"
        f"Client: {client_ens}\n"
        f"DICOM: {dicom_ref}\n"
        f"Timestamp: {timestamp}\n"
        f"Nonce: {nonce}"
    )


def verify_job_request(request: SignedJobRequest, expected_address: str) -> bool:
    """Verify a signed job request."""
    message = create_job_message(
        request.job_type,
        request.client_ens,
        request.dicom_ref,
        request.timestamp,
        request.nonce
    )
    return verify_signature(message, request.signature, expected_address)


# =============================================================================
# Epoch Signing
# =============================================================================

def create_epoch_message(
    epoch_id: str,
    jobs_merkle_root: str,
    jobs_count: int,
    total_distributed: str,
    sealed_at: str
) -> str:
    """Create the canonical message for epoch signing."""
    return (
        f"SwarmOS Epoch Seal\n"
        f"Epoch: {epoch_id}\n"
        f"Merkle Root: {jobs_merkle_root}\n"
        f"Jobs: {jobs_count}\n"
        f"Distributed: {total_distributed}\n"
        f"Sealed: {sealed_at}"
    )


def sign_epoch(
    epoch_id: str,
    jobs_merkle_root: str,
    jobs_count: int,
    total_distributed: str,
    sealed_at: str,
    private_key: str
) -> str:
    """Sign an epoch seal."""
    message = create_epoch_message(
        epoch_id, jobs_merkle_root, jobs_count, total_distributed, sealed_at
    )
    return sign_message(message, private_key)


# =============================================================================
# Merkle Tree
# =============================================================================

def sha256_hex(data: bytes) -> str:
    """Compute SHA256 and return hex string."""
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: dict) -> bytes:
    """Produce canonical JSON bytes for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')


def hash_pair(left: str, right: str) -> str:
    """Hash two hex strings together."""
    combined = bytes.fromhex(left) + bytes.fromhex(right)
    return sha256_hex(combined)


class MerkleTree:
    """Binary Merkle tree for job inclusion proofs."""
    
    def __init__(self, items: list[dict], key_field: str = "id"):
        """
        Build Merkle tree from list of items.
        
        Args:
            items: List of dicts to include in tree
            key_field: Field to sort by for deterministic ordering
        """
        # Sort deterministically
        self.items = sorted(items, key=lambda x: x.get(key_field, ''))
        
        # Compute leaf hashes
        self.leaves: list[str] = []
        self.item_to_index: dict[str, int] = {}
        
        for i, item in enumerate(self.items):
            leaf_hash = sha256_hex(canonical_json(item))
            self.leaves.append(leaf_hash)
            self.item_to_index[item.get(key_field, '')] = i
        
        # Build tree levels
        self.levels: list[list[str]] = [self.leaves.copy()]
        self._build_tree()
    
    def _build_tree(self) -> None:
        """Build tree levels from leaves to root."""
        if not self.leaves:
            return
        
        current_level = self.leaves.copy()
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # Odd number: duplicate last node
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = hash_pair(left, right)
                next_level.append(parent)
            
            self.levels.append(next_level)
            current_level = next_level
    
    @property
    def root(self) -> str:
        """Get Merkle root hash."""
        if not self.levels or not self.levels[-1]:
            return sha256_hex(b'')
        return self.levels[-1][0]
    
    def get_proof(self, item_key: str) -> list[dict] | None:
        """
        Get Merkle proof for an item.
        
        Returns:
            List of {hash, position} dicts, or None if not found
        """
        if item_key not in self.item_to_index:
            return None
        
        index = self.item_to_index[item_key]
        proof = []
        
        for level in self.levels[:-1]:
            level_size = len(level)
            
            if index % 2 == 0:
                sibling_index = index + 1
                position = 'right'
            else:
                sibling_index = index - 1
                position = 'left'
            
            if sibling_index >= level_size:
                sibling_hash = level[index]
            else:
                sibling_hash = level[sibling_index]
            
            proof.append({'hash': sibling_hash, 'position': position})
            index = index // 2
        
        return proof
    
    def get_leaf_hash(self, item_key: str) -> str | None:
        """Get leaf hash for an item."""
        if item_key not in self.item_to_index:
            return None
        return self.leaves[self.item_to_index[item_key]]


def verify_merkle_proof(
    leaf_hash: str,
    proof: list[dict],
    expected_root: str
) -> bool:
    """Verify a Merkle inclusion proof."""
    current = leaf_hash
    
    for step in proof:
        sibling = step['hash']
        position = step['position']
        
        if position == 'left':
            current = hash_pair(sibling, current)
        else:
            current = hash_pair(current, sibling)
    
    return current == expected_root


# =============================================================================
# Receipt Generation
# =============================================================================

@dataclass
class JobReceipt:
    """Cryptographic receipt for a completed job."""
    receipt_version: str
    job_id: str
    epoch_id: str
    client: str
    agent: str
    job_type: str
    price: str
    currency: str
    timing: dict
    leaf_hash: str
    jobs_merkle_root: str
    merkle_proof: list[dict]
    epoch_signature_ref: str


def generate_receipt(
    job: dict,
    epoch_id: str,
    merkle_tree: MerkleTree,
    version: str = "1.1.0"
) -> JobReceipt | None:
    """Generate a job receipt with Merkle inclusion proof."""
    job_id = job.get('id', '')
    
    leaf_hash = merkle_tree.get_leaf_hash(job_id)
    proof = merkle_tree.get_proof(job_id)
    
    if leaf_hash is None or proof is None:
        return None
    
    return JobReceipt(
        receipt_version=version,
        job_id=job_id,
        epoch_id=epoch_id,
        client=job.get('client_ens', ''),
        agent=job.get('worker_ens', ''),
        job_type=job.get('job_type', ''),
        price=str(job.get('fee_usd', '0.10')),
        currency="USD",
        timing={
            'submitted_utc': job.get('submitted_at', ''),
            'started_utc': job.get('started_at', ''),
            'completed_utc': job.get('completed_at', ''),
        },
        leaf_hash=leaf_hash,
        jobs_merkle_root=merkle_tree.root,
        merkle_proof=proof,
        epoch_signature_ref="SIGNATURE.txt"
    )
