# SwarmOS Backend Architecture

## Overview

SwarmOS is sovereign compute infrastructure. This document defines the backend systems that power job execution, settlement, and epoch finalization.

```
Client Request → Bee-1 (Controller) → SwarmRails (Queue) → Bee-2 (Worker) → Result → Epoch → SwarmOrb
```

---

## ENS Identity Map

| ENS | Role | Subdomain Pattern |
|-----|------|-------------------|
| `swarmos.eth` | Controller / Queen | `api.swarmos.eth`, `ledger.swarmos.eth` |
| `swarmbee.eth` | Workers | `bee-01.swarmbee.eth`, `bee-02.swarmbee.eth` |
| `swarmepoch.eth` | Ledger / Settlement | `data.swarmepoch.eth` |
| `swarmorb.eth` | Explorer | `swarmorb.eth.limo` |
| `swarmbank.eth` | Treasury | `vault.swarmbank.eth` |
| `clientswarm.eth` | Clients | `xyzclinic.clientswarm.eth` |

---

## Component Breakdown

### 1. Bee-1 (Controller)

**Location:** `api.swarmos.eth` (resolves to your server IP)

**Responsibilities:**
- Receive signed job requests from clients
- Verify EIP-191 signatures + ENS ownership
- Check client USDC balance
- Create job records in ledger
- Queue jobs for workers
- Route jobs to available workers
- Receive results from workers
- Update ledger with completion
- Deduct client balance
- Trigger epoch sealing

**Tech Stack:**
- Python 3.11+ / FastAPI
- Async everywhere
- Pydantic for validation
- SQLAlchemy for ORM

### 2. Bee-2...N (Workers)

**Location:** `bee-XX.swarmbee.eth` (LAN IPs, not public)

**Responsibilities:**
- Register with Bee-1 on startup
- Send heartbeats every 30s
- Pull jobs from queue
- Execute MONAI inference
- Generate Proof of Execution (PoE) hash
- Return results to Bee-1
- Report hardware stats (GPU, VRAM, utilization)

**Tech Stack:**
- Python 3.11+
- MONAI for medical imaging
- PyTorch + CUDA
- gRPC or HTTP for communication

### 3. SwarmRails (Queue)

**Responsibilities:**
- Job queue (pending → processing → complete)
- Worker registry (online, busy, offline)
- Job routing logic (round-robin, least-busy, GPU-match)
- Dead letter queue for failed jobs
- Retry logic

**Tech Stack:**
- Redis (simple, fast, proven)
- Redis Streams for job queue
- Redis Pub/Sub for worker events

### 4. SwarmLedger (Database)

**Responsibilities:**
- Job records (immutable after completion)
- Epoch records
- Client accounts
- Worker registry
- Payout history

**Tech Stack:**
- SQLite for simplicity (→ Postgres for scale)
- SQLAlchemy ORM
- Alembic for migrations

### 5. SwarmBank (Treasury)

**Responsibilities:**
- Client USDC balances
- Credit top-ups (watch L1 for transfers)
- Balance deductions on job complete
- Payout calculations (Work Pool 70%, Readiness Pool 30%)
- Operator fee (5%), Protocol fee (2%)

**Tech Stack:**
- Web3.py for L1 interaction
- USDC contract monitoring
- Internal balance ledger (off-chain for speed)
- On-chain settlement for withdrawals

### 6. Epoch Sealer (Scheduled Job)

**Responsibilities:**
- Run every 24 hours (or on-demand)
- Collect all completed jobs in epoch
- Compute Merkle root over jobs
- Generate SUMMARY.json
- Generate SIGNATURE.txt (EIP-191 signed by swarmos.eth)
- Calculate payouts per worker
- Pin epoch bundle to IPFS
- Trigger SwarmOrb index update

**Tech Stack:**
- Python script (cron or systemd timer)
- Merkle tree implementation
- eth_account for signing
- IPFS HTTP API for pinning

---

## Data Flow

### Job Submission Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CLIENT SUBMITS JOB                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client (xyz.clientswarm.eth)                                   │
│     │                                                           │
│     │ POST /api/v1/jobs                                         │
│     │ {                                                         │
│     │   "job_type": "spine_mri",                               │
│     │   "dicom_ref": "ipfs://Qm...",                           │
│     │   "client_ens": "xyz.clientswarm.eth",                   │
│     │   "signature": "0x...",                                   │
│     │   "timestamp": 1704067200                                 │
│     │ }                                                         │
│     ▼                                                           │
│  Bee-1 API (api.swarmos.eth)                                   │
│     │                                                           │
│     ├─► Verify signature (EIP-191)                             │
│     ├─► Verify ENS ownership                                    │
│     ├─► Check balance ≥ $0.10                                  │
│     ├─► Create job record (status: pending)                    │
│     ├─► Reserve $0.10 from balance                             │
│     ├─► Queue job in Redis                                      │
│     │                                                           │
│     ▼                                                           │
│  Return: { "job_id": "job-002-0848", "status": "queued" }      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Job Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 2. WORKER EXECUTES JOB                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SwarmRails (Redis)                                             │
│     │                                                           │
│     │ Job available in queue                                    │
│     ▼                                                           │
│  Bee-2 (bee-01.swarmbee.eth)                                   │
│     │                                                           │
│     ├─► Pull job from queue                                     │
│     ├─► Update status: processing                               │
│     ├─► Download DICOM from IPFS                               │
│     ├─► Run MONAI inference                                     │
│     ├─► Generate result + PoE hash                             │
│     │   PoE = sha256(job_id + result_hash + worker_ens)        │
│     ├─► Upload result to IPFS                                   │
│     │                                                           │
│     ▼                                                           │
│  POST /api/v1/jobs/{job_id}/complete                           │
│  {                                                              │
│    "result_ref": "ipfs://Qm...",                               │
│    "poe_hash": "abc123...",                                    │
│    "execution_ms": 2847,                                        │
│    "worker_signature": "0x..."                                  │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Job Settlement Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 3. BEE-1 SETTLES JOB                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Bee-1 receives completion                                      │
│     │                                                           │
│     ├─► Verify worker signature                                 │
│     ├─► Verify PoE hash                                         │
│     ├─► Update job record (status: completed)                  │
│     ├─► Finalize balance deduction ($0.10)                     │
│     ├─► Credit worker for payout (pending epoch)               │
│     ├─► Add job to current epoch batch                         │
│     │                                                           │
│     ▼                                                           │
│  Job available for client to fetch result                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Epoch Sealing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 4. EPOCH SEALS (Every 24h)                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Epoch Sealer (cron job)                                        │
│     │                                                           │
│     ├─► Collect all completed jobs in epoch                    │
│     ├─► Sort jobs by job_id                                     │
│     ├─► Compute Merkle tree                                     │
│     ├─► Generate SUMMARY.json                                   │
│     │   {                                                       │
│     │     "epoch_id": "epoch-002",                             │
│     │     "jobs_merkle_root": "7ec20e03...",                   │
│     │     "treasury": { ... },                                  │
│     │     "agents": { ... },                                    │
│     │     "clients": { ... }                                    │
│     │   }                                                       │
│     ├─► Generate jobs.json, agents.json                        │
│     ├─► Compute hashes for all artifacts                       │
│     ├─► Sign with swarmos.eth key (EIP-191)                    │
│     ├─► Generate SIGNATURE.txt                                  │
│     ├─► Bundle: audit/epoch-002/                               │
│     ├─► Pin to IPFS                                             │
│     ├─► Calculate payouts:                                      │
│     │   - Work Pool (70%) → per job completed                  │
│     │   - Readiness Pool (30%) → per uptime                    │
│     │   - Protocol Fee (2%) → bee23.eth                        │
│     │   - Operator Fee (5%) → swarmos.eth                      │
│     ├─► Record payouts in ledger                               │
│     │                                                           │
│     ▼                                                           │
│  Epoch finalized. SwarmOrb indexer picks up new epoch.         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Jobs Table

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,              -- job-002-0848
    epoch_id TEXT NOT NULL,           -- epoch-002
    client_ens TEXT NOT NULL,         -- xyz.clientswarm.eth
    worker_ens TEXT,                  -- bee-01.swarmbee.eth
    job_type TEXT NOT NULL,           -- spine_mri
    status TEXT NOT NULL,             -- pending, processing, completed, failed
    dicom_ref TEXT,                   -- ipfs://Qm...
    result_ref TEXT,                  -- ipfs://Qm...
    poe_hash TEXT,                    -- proof of execution
    fee_usd DECIMAL(10,2) DEFAULT 0.10,
    execution_ms INTEGER,
    submitted_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Epochs Table

```sql
CREATE TABLE epochs (
    id TEXT PRIMARY KEY,              -- epoch-002
    status TEXT NOT NULL,             -- active, sealing, finalized
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    jobs_count INTEGER DEFAULT 0,
    jobs_merkle_root TEXT,
    total_revenue DECIMAL(10,2) DEFAULT 0,
    total_distributed DECIMAL(10,2) DEFAULT 0,
    signature TEXT,                   -- EIP-191 signature
    ipfs_hash TEXT,                   -- Qm...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Clients Table

```sql
CREATE TABLE clients (
    ens TEXT PRIMARY KEY,             -- xyz.clientswarm.eth
    balance_usd DECIMAL(10,2) DEFAULT 0,
    reserved_usd DECIMAL(10,2) DEFAULT 0,
    total_spent_usd DECIMAL(10,2) DEFAULT 0,
    total_jobs INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Workers Table

```sql
CREATE TABLE workers (
    ens TEXT PRIMARY KEY,             -- bee-01.swarmbee.eth
    status TEXT NOT NULL,             -- online, busy, offline, draining
    gpu_model TEXT,
    vram_gb INTEGER,
    current_job_id TEXT,
    jobs_completed INTEGER DEFAULT 0,
    total_earned_usd DECIMAL(10,2) DEFAULT 0,
    uptime_seconds INTEGER DEFAULT 0,
    last_heartbeat TIMESTAMP,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Payouts Table

```sql
CREATE TABLE payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id TEXT NOT NULL,
    worker_ens TEXT NOT NULL,
    work_share_usd DECIMAL(10,2) DEFAULT 0,
    readiness_share_usd DECIMAL(10,2) DEFAULT 0,
    total_payout_usd DECIMAL(10,2) DEFAULT 0,
    jobs_completed INTEGER DEFAULT 0,
    uptime_seconds INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',    -- pending, paid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Credit Transactions Table

```sql
CREATE TABLE credit_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_ens TEXT NOT NULL,
    tx_type TEXT NOT NULL,            -- deposit, job_charge, refund
    amount_usd DECIMAL(10,2) NOT NULL,
    balance_after DECIMAL(10,2) NOT NULL,
    reference TEXT,                   -- job_id or tx_hash
    eth_tx_hash TEXT,                 -- L1 transaction hash
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Endpoints

### Jobs API

```
POST   /api/v1/jobs                    # Submit new job
GET    /api/v1/jobs/{job_id}           # Get job status
GET    /api/v1/jobs/{job_id}/result    # Get job result
GET    /api/v1/jobs/{job_id}/receipt   # Get Merkle receipt
GET    /api/v1/jobs?client={ens}       # List client jobs
```

### Workers API (Internal)

```
POST   /api/v1/workers/register        # Worker registration
POST   /api/v1/workers/heartbeat       # Worker heartbeat
POST   /api/v1/jobs/{job_id}/claim     # Claim job from queue
POST   /api/v1/jobs/{job_id}/complete  # Submit job completion
```

### Clients API

```
GET    /api/v1/clients/{ens}           # Get client info
GET    /api/v1/clients/{ens}/balance   # Get balance
POST   /api/v1/clients/{ens}/topup     # Record L1 deposit
GET    /api/v1/clients/{ens}/history   # Transaction history
```

### Epochs API

```
GET    /api/v1/epochs                  # List all epochs
GET    /api/v1/epochs/current          # Get current epoch
GET    /api/v1/epochs/{id}             # Get epoch details
GET    /api/v1/epochs/{id}/jobs        # Get epoch jobs
GET    /api/v1/epochs/{id}/payouts     # Get epoch payouts
```

---

## Directory Structure

```
swarmos/
├── bee1/                           # Controller (Bee-1)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── jobs.py             # Job endpoints
│   │   │   ├── workers.py          # Worker endpoints
│   │   │   ├── clients.py          # Client endpoints
│   │   │   └── epochs.py           # Epoch endpoints
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── auth.py             # Signature verification
│   │   └── deps.py                 # Dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Settings
│   │   ├── queue.py                # Redis queue
│   │   ├── router.py               # Job routing
│   │   └── ledger.py               # DB operations
│   ├── Dockerfile
│   └── requirements.txt
│
├── bee2/                           # Worker template (Bee-2...N)
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── main.py                 # Worker daemon
│   │   ├── executor.py             # Job execution
│   │   ├── heartbeat.py            # Health reporting
│   │   └── inference/
│   │       ├── __init__.py
│   │       ├── base.py             # Base inference class
│   │       ├── spine_mri.py        # Spine analysis
│   │       └── brain_mri.py        # Brain segmentation
│   ├── Dockerfile
│   └── requirements.txt
│
├── rails/                          # Shared libraries
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── session.py              # DB session
│   │   └── migrations/             # Alembic migrations
│   ├── queue/
│   │   ├── __init__.py
│   │   └── redis.py                # Redis client
│   ├── crypto/
│   │   ├── __init__.py
│   │   ├── ens.py                  # ENS resolution
│   │   ├── signing.py              # EIP-191 signing
│   │   └── merkle.py               # Merkle tree
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── job.py                  # Job schemas
│   │   ├── epoch.py                # Epoch schemas
│   │   └── receipt.py              # Receipt schemas
│   └── utils/
│       ├── __init__.py
│       └── ipfs.py                 # IPFS client
│
├── epoch-sealer/                   # Epoch finalization
│   ├── __init__.py
│   ├── sealer.py                   # Main sealer logic
│   ├── payout.py                   # Payout calculations
│   ├── publisher.py                # IPFS publishing
│   └── Dockerfile
│
├── orb-sync/                       # SwarmOrb integration
│   ├── __init__.py
│   ├── indexer.py                  # Generate index.json
│   └── watcher.py                  # Watch for new epochs
│
├── docker-compose.yml              # Local dev stack
├── docker-compose.prod.yml         # Production stack
├── .env.example
├── Makefile
└── README.md
```

---

## Configuration

### Environment Variables

```bash
# Bee-1 Controller
BEE1_HOST=0.0.0.0
BEE1_PORT=8000
BEE1_ENS=swarmos.eth
BEE1_PRIVATE_KEY=0x...           # For signing epochs

# Database
DATABASE_URL=sqlite:///./swarmledger.db
# DATABASE_URL=postgresql://user:pass@localhost/swarmledger

# Redis
REDIS_URL=redis://localhost:6379/0

# IPFS
IPFS_API_URL=http://localhost:5001

# Ethereum L1
ETH_RPC_URL=https://mainnet.infura.io/v3/...
USDC_CONTRACT=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

# Epochs
EPOCH_DURATION_HOURS=24
WORK_POOL_PCT=70
READINESS_POOL_PCT=30
PROTOCOL_FEE_PCT=2
OPERATOR_FEE_PCT=5

# Job Pricing
JOB_FEE_USD=0.10
```

---

## Deployment

### Single Rack Setup

```
┌─────────────────────────────────────────────────────────────┐
│                      YOUR RACK                               │
│                                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Bee-1   │  │ Redis   │  │ SQLite  │  │ IPFS    │       │
│  │ :8000   │  │ :6379   │  │ (file)  │  │ :5001   │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
│       │            │            │            │              │
│       └────────────┴────────────┴────────────┘              │
│                         │                                    │
│                    LAN (10.0.0.x)                           │
│                         │                                    │
│       ┌─────────────────┼─────────────────┐                 │
│       │                 │                 │                 │
│  ┌────┴────┐      ┌────┴────┐      ┌────┴────┐            │
│  │ Bee-2   │      │ Bee-3   │      │ Bee-N   │            │
│  │ GPU x8  │      │ GPU x8  │      │ GPU x8  │            │
│  │ 5090s   │      │ 6000Ada │      │ 3090s   │            │
│  └─────────┘      └─────────┘      └─────────┘            │
│                                                              │
│  SOLAR POWER ──► BATTERY BACKUP ──► PDUs ──► RACKS         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Docker Compose (Dev)

```yaml
version: '3.8'

services:
  bee1:
    build: ./bee1
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/swarmledger.db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  ipfs:
    image: ipfs/kubo:latest
    ports:
      - "5001:5001"
      - "8080:8080"
    volumes:
      - ipfs_data:/data/ipfs

  epoch-sealer:
    build: ./epoch-sealer
    environment:
      - DATABASE_URL=sqlite:///./data/swarmledger.db
    volumes:
      - ./data:/app/data
      - ./audit:/app/audit

volumes:
  redis_data:
  ipfs_data:
```

---

## Security Considerations

### Authentication
- All client requests signed with EIP-191
- ENS ownership verified on-chain
- No passwords, no sessions, no cookies

### Network
- Bee-1 API: Public (HTTPS via Cloudflare or nginx)
- Bee-2...N: LAN only (no public exposure)
- Redis: LAN only
- Database: Local file or LAN-only Postgres

### Data
- DICOM data: Encrypted at rest, deleted after processing
- Results: Stored on IPFS (content-addressed)
- Keys: Hardware security module (HSM) for swarmos.eth signing key

### Audit
- All jobs logged immutably
- Epochs sealed with Merkle proofs
- Full audit trail via SwarmOrb

---

## Scaling Path

### Phase 1: Single Rack (Current)
- 1 Bee-1, N Bee-2 workers
- SQLite database
- Single Redis instance

### Phase 2: Multi-Rack
- Bee-1 replicas behind load balancer
- Postgres with read replicas
- Redis Cluster

### Phase 3: Federated
- Multiple independent SwarmOS operators
- Shared epoch ledger
- Cross-operator job routing

---

## Next Steps

1. **Implement Bee-1 API** — FastAPI with job submission
2. **Implement Bee-2 Worker** — MONAI inference executor
3. **Implement Epoch Sealer** — Merkle + IPFS + signing
4. **Connect to SwarmOrb** — Index generation
5. **Deploy to rack** — Docker Compose

---

*This is the engine. Everything else is glass.*

🐝⚡
