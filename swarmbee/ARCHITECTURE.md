# SwarmBee Architecture

## Overview

**swarmbee.eth** is the worker identity layer for SwarmOS. Every GPU operator gets a subdomain that serves as their on-chain identity.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SWARMBEE                                  │
│                                                                  │
│   The Hive. The Workers. The Miners.                            │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                 WORKER REGISTRY                          │  │
│   │                                                          │  │
│   │  bee-01.swarmbee.eth ──── RTX 5090 x8 ──── ONLINE       │  │
│   │  bee-02.swarmbee.eth ──── RTX 6000 Ada x8 ── BUSY       │  │
│   │  bee-03.swarmbee.eth ──── RTX 3090 x8 ──── ONLINE       │  │
│   │  bee-04.swarmbee.eth ──── RTX 5090 x8 ──── ONLINE       │  │
│   │  bee-05.swarmbee.eth ──── RTX 6000 Ada x8 ── BUSY       │  │
│   │  ...                                                     │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Identity System

### ENS Subdomains

Every worker gets an ENS subdomain under swarmbee.eth:

```
swarmbee.eth (parent)
├── bee-01.swarmbee.eth
├── bee-02.swarmbee.eth
├── bee-03.swarmbee.eth
├── ...
└── your-name.swarmbee.eth
```

### Worker Ownership

- Workers own their subdomain private key
- Key proves identity when signing jobs
- Earnings tied to ENS identity
- Export/backup supported

---

## Hardware Fleet

| GPU Model | Count | VRAM/GPU | Total VRAM |
|-----------|-------|----------|------------|
| RTX 5090 | 48 | 32 GB | 1.5 TB |
| RTX 6000 Ada | 48 | 48 GB | 2.3 TB |
| RTX 3090 | 200 | 24 GB | 4.8 TB |
| **Total** | **296** | — | **8.6 TB** |

### Power Infrastructure

- Solar array: Primary power
- Battery backup: 24h autonomy
- Grid connection: Failover only

---

## Worker Lifecycle

### 1. Registration

```
Worker node starts
    │
    │ POST /api/v1/workers/register
    │ {
    │   ens: "bee-01.swarmbee.eth",
    │   gpu_model: "RTX 5090",
    │   gpu_count: 8,
    │   vram_gb: 256,
    │   signature: "0x..."
    │ }
    ▼
Bee-1 verifies ENS ownership
    │
    │ Adds to worker registry
    ▼
Worker marked ONLINE
```

### 2. Heartbeat

```
Every 30 seconds:
    │
    │ POST /api/v1/workers/heartbeat
    │ {
    │   ens: "bee-01.swarmbee.eth",
    │   status: "online",
    │   gpu_utilization: 45.2,
    │   current_job: null
    │ }
    ▼
Bee-1 updates last_heartbeat
    │
    │ If no heartbeat for 60s → mark OFFLINE
```

### 3. Job Execution

```
Worker polls for job
    │
    │ POST /api/v1/jobs/claim
    ▼
Bee-1 assigns job
    │
    │ Worker status → BUSY
    ▼
Worker executes MONAI inference
    │
    │ Generates Proof of Execution
    ▼
Worker submits completion
    │
    │ POST /api/v1/jobs/{id}/complete
    │ {
    │   result_ref: "ipfs://Qm...",
    │   poe_hash: "abc123...",
    │   execution_ms: 2847
    │ }
    ▼
Bee-1 records completion
    │
    │ Worker status → ONLINE
    │ Worker earnings += $0.07
```

### 4. Epoch Settlement

```
Every 24h:
    │
    │ Epoch sealer calculates payouts
    │
    │ Work Pool (70%): Per job completed
    │ Readiness Pool (30%): Per uptime
    ▼
SwarmLedger finalizes earnings
    │
    │ Worker can withdraw USDC
```

---

## Worker Status

| Status | Description |
|--------|-------------|
| `online` | Ready for jobs |
| `busy` | Currently processing |
| `draining` | Finishing current job, then stopping |
| `offline` | Not responding to heartbeats |

---

## API Endpoints

### SwarmBee Registry (api.swarmbee.eth)

```
GET  /v1/stats               # Swarm-wide statistics
GET  /v1/workers             # List all workers
GET  /v1/workers/{ens}       # Get specific worker
GET  /v1/hardware            # Hardware inventory
GET  /v1/leaderboard         # Top workers by jobs
```

### Bee-1 Worker Endpoints

```
POST /api/v1/workers/register    # Register worker
POST /api/v1/workers/heartbeat   # Send heartbeat
POST /api/v1/jobs/claim          # Claim next job
POST /api/v1/jobs/{id}/complete  # Submit completion
```

---

## Economics

### Per Job

```
Job Fee: $0.10

Distribution:
├── Worker earnings: $0.07 (70% of work pool after fees)
├── Readiness pool: $0.02 (30% distributed by uptime)
├── Protocol fee: $0.002 (2% → bee23.eth)
└── Operator fee: $0.005 (5% → swarmos.eth)
```

### Monthly Potential (per 8-GPU node)

```
Jobs/day: ~500 (assuming steady flow)
Daily earnings: ~$35
Monthly earnings: ~$1,050

+ Readiness pool bonus for high uptime
```

---

## Joining the Swarm

### Requirements

1. **Hardware**: NVIDIA GPU with 24GB+ VRAM
2. **Network**: Static IP or domain, reliable connection
3. **Identity**: ENS subdomain (*.swarmbee.eth)
4. **Software**: Docker + NVIDIA runtime

### Setup

```bash
# 1. Get subdomain
# Contact SwarmOS operator for bee-XX.swarmbee.eth

# 2. Configure worker
export WORKER_ENS=bee-XX.swarmbee.eth
export WORKER_PRIVATE_KEY=0x...
export GPU_MODEL="RTX 5090"
export VRAM_GB=256
export BEE1_URL=https://api.swarmos.eth.limo

# 3. Run worker
docker run -d \
  --gpus all \
  -e WORKER_ENS=$WORKER_ENS \
  -e WORKER_PRIVATE_KEY=$WORKER_PRIVATE_KEY \
  -e GPU_MODEL="$GPU_MODEL" \
  -e VRAM_GB=$VRAM_GB \
  -e BEE1_URL=$BEE1_URL \
  swarmos/bee2:latest

# 4. Verify registration
curl https://api.swarmbee.eth.limo/v1/workers/$WORKER_ENS
```

---

## Security

| Layer | Implementation |
|-------|----------------|
| Identity | ENS subdomain ownership |
| Auth | EIP-191 signatures on all requests |
| Network | Workers on LAN, only Bee-1 public |
| Execution | Sandboxed inference containers |
| Audit | All jobs logged with PoE hashes |

---

## Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ClientSwarm ──► Bee-1 ──► SwarmBee Workers ──► Results         │
│       │                          │                               │
│       │                          ▼                               │
│       │                    SwarmLedger                          │
│       │                    (earnings)                            │
│       │                          │                               │
│       │                          ▼                               │
│       └──────────────────► SwarmOrb                             │
│                            (verification)                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*The hive that works. Every bee an identity. Every job proven.*

🐝⚡
