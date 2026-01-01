// src/signing.rs
use anyhow::{anyhow, Result};
use ethers::core::k256::ecdsa::SigningKey;
use ethers::core::types::{Address, Signature, H256};
use ethers::signers::{LocalWallet, Signer};
use ethers::utils::keccak256;
use serde_json::Value;

pub fn canonical_json_bytes(v: &Value) -> Result<Vec<u8>> {
    // Canonical JSON: stable key order, no whitespace.
    // serde_json preserves map order as inserted; we must sort keys.
    let normalized = sort_json(v);
    Ok(serde_json::to_vec(&normalized)?)
}

fn sort_json(v: &Value) -> Value {
    match v {
        Value::Object(map) => {
            let mut keys: Vec<_> = map.keys().cloned().collect();
            keys.sort();
            let mut new_map = serde_json::Map::new();
            for k in keys {
                new_map.insert(k.clone(), sort_json(&map[&k]));
            }
            Value::Object(new_map)
        }
        Value::Array(arr) => Value::Array(arr.iter().map(sort_json).collect()),
        _ => v.clone(),
    }
}

/// Compute keccak256 over canonical JSON bytes, excluding signing.signature.
/// You should pass a snapshot JSON where signing.signature is empty or removed.
pub fn payload_hash_keccak(snapshot: &Value) -> Result<[u8; 32]> {
    let mut snap = snapshot.clone();

    // Remove signing.signature if present
    if let Some(signing) = snap.get_mut("signing") {
        if let Some(obj) = signing.as_object_mut() {
            obj.remove("signature");
        }
    }

    let bytes = canonical_json_bytes(&snap)?;
    Ok(keccak256(bytes))
}

/// Convert [u8;32] to "keccak256:<hex>"
pub fn hash_str(hash: [u8; 32]) -> String {
    format!("keccak256:{}", hex::encode(hash))
}

/// Load LocalWallet from a hex private key (0x... or raw hex)
pub fn wallet_from_private_key_hex(pk_hex: &str) -> Result<LocalWallet> {
    let pk_hex = pk_hex.trim().strip_prefix("0x").unwrap_or(pk_hex.trim());
    let bytes = hex::decode(pk_hex).map_err(|e| anyhow!("bad hex private key: {e}"))?;
    if bytes.len() != 32 {
        return Err(anyhow!("private key must be 32 bytes (64 hex chars)"));
    }
    let signing_key = SigningKey::from_bytes(bytes.as_slice().into())
        .map_err(|e| anyhow!("invalid private key: {e}"))?;
    let wallet: LocalWallet = LocalWallet::from(signing_key);
    Ok(wallet)
}

/// EIP-191 signing of 32-byte hash (as message bytes)
/// Returns signature bytes (65) and recovered address
pub async fn sign_eip191_hash(wallet: &LocalWallet, hash: [u8; 32]) -> Result<(Signature, Address)> {
    // EIP-191: sign_message applies the "\x19Ethereum Signed Message:\n" prefix
    let sig = wallet.sign_message(hash).await?;
    let addr = wallet.address();

    // Safety check: ensure signature recovers to addr
    let recovered = sig.recover(hash)?;
    if recovered != addr {
        return Err(anyhow!("signature recovery mismatch"));
    }
    Ok((sig, addr))
}

/// Attach signing fields into snapshot:
/// - signing.payload_hash
/// - signing.signature = eip191:0x...
pub fn attach_signature(snapshot: &mut Value, payload_hash: [u8; 32], sig: &Signature) -> Result<()> {
    let signing = snapshot
        .get_mut("signing")
        .ok_or_else(|| anyhow!("snapshot missing signing object"))?
        .as_object_mut()
        .ok_or_else(|| anyhow!("signing must be object"))?;

    signing.insert("payload_hash".to_string(), Value::String(hash_str(payload_hash)));
    signing.insert(
        "signature".to_string(),
        Value::String(format!("eip191:0x{}", sig.to_string().trim_start_matches("0x"))),
    );
    signing.insert("scheme".to_string(), Value::String("eip191".to_string()));

    Ok(())
}

/// Verify signature matches payload hash and expected address.
/// (ENS owner verification is a later layer; this verifies crypto correctness.)
pub fn verify_eip191(snapshot: &Value, expected_addr: Address) -> Result<()> {
    let signing = snapshot
        .get("signing")
        .and_then(|v| v.as_object())
        .ok_or_else(|| anyhow!("missing signing object"))?;

    let payload_hash_str = signing
        .get("payload_hash")
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow!("missing signing.payload_hash"))?;

    let sig_str = signing
        .get("signature")
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow!("missing signing.signature"))?;

    let hash_hex = payload_hash_str
        .strip_prefix("keccak256:")
        .ok_or_else(|| anyhow!("payload_hash must start with keccak256:"))?;
    let hash_bytes = hex::decode(hash_hex)?;
    if hash_bytes.len() != 32 {
        return Err(anyhow!("payload hash must be 32 bytes"));
    }
    let mut hash = [0u8; 32];
    hash.copy_from_slice(&hash_bytes);

    let sig_hex = sig_str
        .strip_prefix("eip191:0x")
        .ok_or_else(|| anyhow!("signature must start with eip191:0x"))?;
    let sig_bytes = hex::decode(sig_hex)?;
    if sig_bytes.len() != 65 {
        return Err(anyhow!("signature must be 65 bytes"));
    }

    let sig = Signature::try_from(sig_bytes.as_slice())?;
    let recovered = sig.recover(H256::from(hash))?;

    if recovered != expected_addr {
        return Err(anyhow!("signature does not recover to expected address"));
    }

    // Recompute payload hash from snapshot content (excluding signature)
    let recomputed = payload_hash_keccak(snapshot)?;
    if recomputed != hash {
        return Err(anyhow!("payload_hash mismatch: snapshot content changed"));
    }

    Ok(())
}
