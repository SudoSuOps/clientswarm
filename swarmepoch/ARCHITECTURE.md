# SwarmEpoch Architecture

## Overview

**swarmepoch.eth** is the immutable archive for SwarmOS. Every sealed epoch is stored here with Merkle roots, signatures, and full job histories.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SWARMEPOCH                                │
│                                                                  │
│   The Archive. The History. The Proof.                          │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    EPOCH TIMELINE                        │  │
│   │                                                          │  │
│   │  epoch-000 ─── Genesis ─────────────── Jan 1, 2025      │  │
│   │       │                                                  │  │
│   │       ▼                                                  │  │
│   │  epoch-001 ─── 105 jobs ─── $10.50 ─── Jan 16, 2025    │  │
│   │       │                                                  │  │
│   │       ▼                                                  │  │
│   │  epoch-002 ─── 248 jobs ─── $24.80 ─── Jan 17, 2025    │  │
│   │       │                                                  │  │
│   │       ▼                                                  │  │
│   │  epoch-003 ─── (active) ─── $6.70 ─── (pending)        │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Epoch Lifecycle

### 1. Creation

```
Previous epoch seals at 00:00 UTC
         │
         ▼
New epoch created
         │
         │ epoch_id = epoch-XXX
         │ status = "active"
         │ start_time = now()
         ▼
Jobs accumulate during epoch
```

### 2. Accumulation

```
During active epoch:
         │
         │ Jobs submitted → completed
         │ Balances charged
         │ Worker earnings credited (pending)
         ▼
Epoch tracks:
  - jobs_count
  - total_revenue
  - participating agents
  - participating clients
```

### 3. Sealing

```
At epoch end (00:00 UTC next day):
         │
         │ 1. Collect all completed jobs
         │ 2. Sort by job_id (deterministic)
         │ 3. Build Merkle tree
         │ 4. Calculate payouts
         ▼
Generate epoch bundle:
  - SUMMARY.json
  - jobs.json
  - agents.json
  - SIGNATURE.txt
         │
         ▼
Sign with swarmos.eth key (EIP-191)
         │
         ▼
Pin to IPFS
         │
         ▼
status = "finalized"
```

---

## Epoch Bundle Structure

```
audit/epoch-002/
├── SUMMARY.json       # Epoch overview
├── jobs.json          # All jobs with PoE
├── agents.json        # Worker stats
└── SIGNATURE.txt      # EIP-191 signature
```

### SUMMARY.json

```json
{
  "version": "1.1.0",
  "epoch_id": "epoch-002",
  "status": "finalized",
  "sealed_at": "2025-01-17T00:00:00Z",
  
  "jobs": {
    "count": 248,
    "merkle_root": "a3f891c2e7d4b5f6a8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1"
  },
  
  "treasury": {
    "total_revenue_usd": "24.80",
    "work_pool_usd": "16.18",
    "readiness_pool_usd": "6.94",
    "protocol_fee_usd": "0.50",
    "operator_fee_usd": "1.24",
    "total_distributed_usd": "24.80"
  },
  
  "agents_count": 5,
  "clients_count": 12,
  
  "hashes": {
    "summary": "sha256:abc123...",
    "jobs": "sha256:def456...",
    "agents": "sha256:789ghi..."
  }
}
```

### jobs.json

```json
{
  "epoch_id": "epoch-002",
  "jobs_count": 248,
  "jobs": [
    {
      "id": "job-002-0001",
      "client": "xyz.clientswarm.eth",
      "agent": "bee-01.swarmbee.eth",
      "type": "spine_mri",
      "fee_usd": "0.10",
      "execution_ms": 2847,
      "poe_hash": "7ec20e03b05b7898...",
      "submitted_at": "2025-01-16T08:23:45Z",
      "completed_at": "2025-01-16T08:23:48Z"
    },
    // ... 247 more jobs
  ]
}
```

### agents.json

```json
{
  "epoch_id": "epoch-002",
  "agents": [
    {
      "ens": "bee-01.swarmbee.eth",
      "jobs_completed": 87,
      "uptime_seconds": 86400,
      "poe_success_rate": 1.0,
      "work_share_usd": "5.66",
      "readiness_share_usd": "1.39",
      "total_payout_usd": "7.05"
    },
    {
      "ens": "bee-02.swarmbee.eth",
      "jobs_completed": 64,
      "uptime_seconds": 86400,
      "poe_success_rate": 1.0,
      "work_share_usd": "4.16",
      "readiness_share_usd": "1.39",
      "total_payout_usd": "5.55"
    }
    // ... more agents
  ]
}
```

### SIGNATURE.txt

```
SwarmOS Epoch Seal

Epoch: epoch-002
Merkle Root: a3f891c2e7d4b5f6a8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1
Jobs: 248
Distributed: 24.80
Sealed: 2025-01-17T00:00:00Z

---
Signer: swarmos.eth
Address: 0x742d35Cc6634C0532925a3b844Bc9e7595f7e3e0
Signature: 0x8a3f7c2b1e9d4f6a8b0c3e5d7f9a2b4c6e8d0f1a3b5c7d9e1f3a5b7c9d0e2f4...
```

---

## Merkle Tree

### Construction

```
Jobs sorted by job_id (deterministic order)
         │
         ▼
Leaf hashes = sha256(canonical_json(job))
         │
         ▼
Build binary tree:

              [ROOT]
             /      \
         [H01]      [H23]
         /   \      /   \
       [H0] [H1]  [H2] [H3]
        │    │     │    │
       J0   J1    J2   J3
```

### Verification

```python
def verify_job_inclusion(job, proof, expected_root):
    """Verify job is included in epoch."""
    
    # Compute leaf hash
    leaf = sha256(canonical_json(job))
    
    # Walk proof path
    current = leaf
    for step in proof:
        sibling = step['hash']
        if step['position'] == 'left':
            current = sha256(sibling + current)
        else:
            current = sha256(current + sibling)
    
    return current == expected_root
```

---

## API Endpoints

### SwarmEpoch Data API (data.swarmepoch.eth)

```
GET  /v1/epochs                    # List all epochs
GET  /v1/epochs/current            # Current active epoch
GET  /v1/epochs/{id}               # Epoch summary
GET  /v1/epochs/{id}/jobs          # All jobs in epoch
GET  /v1/epochs/{id}/agents        # Agent stats
GET  /v1/epochs/{id}/signature     # EIP-191 signature
GET  /v1/epochs/{id}/ipfs          # IPFS hash

GET  /v1/jobs/{job_id}/receipt     # Job receipt with proof
POST /v1/verify                    # Verify a receipt
```

---

## Storage

### IPFS Pinning

Every sealed epoch is pinned to IPFS:

```
ipfs://QmYwAPJzv5CZsnAzt8auVZRn.../audit/epoch-002/
├── SUMMARY.json
├── jobs.json
├── agents.json
└── SIGNATURE.txt
```

### ENS Content Hash

swarmepoch.eth content hash points to latest index:

```
swarmepoch.eth
└── contenthash: ipfs://QmIndex.../
    └── index.json
        {
          "latest_epoch": "epoch-002",
          "epochs": {
            "epoch-001": "ipfs://Qm.../",
            "epoch-002": "ipfs://Qm.../"
          }
        }
```

---

## Integration

### SwarmOrb Reads From Here

```
SwarmOrb (swarmorb.eth.limo)
         │
         │ Fetch index.json
         ▼
swarmepoch.eth contenthash
         │
         │ Fetch epoch data
         ▼
Display in explorer UI
```

### SwarmLedger Writes Here

```
Epoch Sealer
         │
         │ Finalize epoch
         ▼
Generate bundle
         │
         │ Pin to IPFS
         ▼
Update swarmepoch.eth contenthash
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  JOBS EXECUTE                                                   │
│       │                                                          │
│       ▼                                                          │
│  EPOCH ACCUMULATES (24h)                                        │
│       │                                                          │
│       ▼                                                          │
│  EPOCH SEALER                                                   │
│       │                                                          │
│       ├─► Build Merkle tree                                     │
│       ├─► Calculate payouts                                      │
│       ├─► Generate bundle                                       │
│       ├─► Sign with swarmos.eth                                 │
│       │                                                          │
│       ▼                                                          │
│  PIN TO IPFS ──────────────────────────► swarmepoch.eth         │
│       │                                                          │
│       ▼                                                          │
│  SWARMLEDGER                                                    │
│       │                                                          │
│       ├─► Finalize worker earnings                              │
│       ├─► Record epoch settlement                               │
│       │                                                          │
│       ▼                                                          │
│  SWARMORB                                                       │
│       │                                                          │
│       └─► Update explorer index                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
swarmepoch/
├── ARCHITECTURE.md
├── landing/
│   └── index.html           # swarmepoch.eth.limo
├── api/
│   └── main.py              # Data API
├── sealer/
│   ├── __init__.py
│   ├── sealer.py            # Main sealing logic
│   ├── merkle.py            # Merkle tree
│   ├── bundle.py            # Bundle generation
│   └── publisher.py         # IPFS publishing
├── Dockerfile
└── requirements.txt
```

---

## Security

| Layer | Implementation |
|-------|----------------|
| Integrity | Merkle roots over all jobs |
| Authenticity | EIP-191 signature by swarmos.eth |
| Availability | IPFS pinning (redundant) |
| Immutability | Content-addressed (CID) |
| Verifiability | Anyone can verify proofs |

---

## Economics

Each epoch settles:

```
Total Revenue: $24.80 (248 jobs × $0.10)

Distribution:
├── Work Pool (70%): $17.36
│   └── Split by jobs completed
├── Readiness Pool (30%): $7.44
│   └── Split by uptime
├── Less fees:
│   ├── Protocol (2%): $0.50 → bee23.eth
│   └── Operator (5%): $1.24 → swarmos.eth
│
└── Total Distributed: $24.80
```

---

*Every epoch is a block. Every job is proven. Forever.*

📦⚡
