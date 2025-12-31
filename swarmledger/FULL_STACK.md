# SwarmOS Full Stack Integration

## Complete ENS Identity Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SWARMOS IDENTITY STACK                               │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         PROTOCOL LAYER                                 │ │
│  │                                                                        │ │
│  │    bee23.eth ─────────────── The Law                                  │ │
│  │    │                         Protocol rules, immutable                │ │
│  │    │                                                                  │ │
│  └────┼──────────────────────────────────────────────────────────────────┘ │
│       │                                                                      │
│  ┌────┼──────────────────────────────────────────────────────────────────┐ │
│  │    ▼                       CONTROL LAYER                              │ │
│  │                                                                        │ │
│  │    swarmos.eth ──────────── The Queen                                 │ │
│  │    │                        Coordination, routing, epochs             │ │
│  │    │                                                                  │ │
│  │    ├── api.swarmos.eth      Bee-1 Controller API                     │ │
│  │    └── *.swarmos.eth        Future subdomains                        │ │
│  │                                                                        │ │
│  └────┼──────────────────────────────────────────────────────────────────┘ │
│       │                                                                      │
│  ┌────┼──────────────────────────────────────────────────────────────────┐ │
│  │    ▼                       COMPUTE LAYER                              │ │
│  │                                                                        │ │
│  │    swarmbee.eth ─────────── The Bees                                  │ │
│  │    │                        Workers, miners, GPU operators            │ │
│  │    │                                                                  │ │
│  │    ├── bee-01.swarmbee.eth  Worker node 1 (RTX 5090s)                │ │
│  │    ├── bee-02.swarmbee.eth  Worker node 2 (RTX 6000 Ada)             │ │
│  │    ├── bee-03.swarmbee.eth  Worker node 3 (RTX 3090s)                │ │
│  │    └── ...                  Additional workers                        │ │
│  │                                                                        │ │
│  └────┼──────────────────────────────────────────────────────────────────┘ │
│       │                                                                      │
│  ┌────┼──────────────────────────────────────────────────────────────────┐ │
│  │    ▼                       CLIENT LAYER                               │ │
│  │                                                                        │ │
│  │    clientswarm.eth ──────── The Clients                               │ │
│  │    │                        Clinics, customers, buyers                │ │
│  │    │                                                                  │ │
│  │    ├── xyz.clientswarm.eth       XYZ Orthopedic Clinic               │ │
│  │    ├── acme.clientswarm.eth      ACME Medical                        │ │
│  │    ├── metro.clientswarm.eth     Metro Imaging                       │ │
│  │    └── ...                       Additional clients                   │ │
│  │                                                                        │ │
│  └────┼──────────────────────────────────────────────────────────────────┘ │
│       │                                                                      │
│  ┌────┼──────────────────────────────────────────────────────────────────┐ │
│  │    ▼                       SETTLEMENT LAYER                           │ │
│  │                                                                        │ │
│  │    swarmledger.eth ──────── The Ledger ⭐ NEW                         │ │
│  │    │                        Balances, settlements, payments           │ │
│  │    │                                                                  │ │
│  │    ├── api.swarmledger.eth  Ledger API                               │ │
│  │    └── vault.swarmledger.eth USDC vault address                      │ │
│  │                                                                        │ │
│  │    swarmepoch.eth ───────── The Epochs                                │ │
│  │    │                        Sealed blocks, Merkle roots               │ │
│  │    │                                                                  │ │
│  │    └── data.swarmepoch.eth  Epoch data archive                       │ │
│  │                                                                        │ │
│  │    swarmbank.eth ────────── The Treasury                              │ │
│  │                             USDC holdings, payout pool               │ │
│  │                                                                        │ │
│  └────┼──────────────────────────────────────────────────────────────────┘ │
│       │                                                                      │
│  ┌────┼──────────────────────────────────────────────────────────────────┐ │
│  │    ▼                       WITNESS LAYER                              │ │
│  │                                                                        │ │
│  │    swarmorb.eth ─────────── The Orb                                   │ │
│  │                             Explorer, verification, truth            │ │
│  │                                                                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## eth.limo Deployment Map

| ENS | URL | Status | Purpose |
|-----|-----|--------|---------|
| swarmorb.eth | swarmorb.eth.limo | ✅ LIVE | Epoch explorer |
| swarmos.eth | swarmos.eth.limo | 📦 READY | OS landing page |
| clientswarm.eth | clientswarm.eth.limo | 📦 READY | Client portal |
| swarmledger.eth | swarmledger.eth.limo | 📦 READY | Ledger explorer |
| swarmbee.eth | swarmbee.eth.limo | ⏳ TODO | Worker registry |
| swarmepoch.eth | swarmepoch.eth.limo | ⏳ TODO | Epoch archive |
| swarmbank.eth | swarmbank.eth.limo | ⏳ TODO | Treasury dashboard |
| bee23.eth | bee23.eth.limo | ⏳ TODO | Protocol docs |

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SWARMOS SERVICES                                   │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   BEE-1     │  │   LEDGER    │  │   REDIS     │  │   IPFS      │       │
│  │  :8000      │  │   :8100     │  │   :6379     │  │   :5001     │       │
│  │             │  │             │  │             │  │             │       │
│  │ Controller  │◄►│ Settlement  │◄►│ Job Queue   │◄►│ Content     │       │
│  │ API         │  │ API         │  │ Workers     │  │ Storage     │       │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └─────────────┘       │
│         │                │                                                   │
│         │                │                                                   │
│         ▼                ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SQLITE / POSTGRES                            │   │
│  │                                                                       │   │
│  │  swarmledger.db                                                      │   │
│  │  ├── accounts (clients, workers, treasury)                           │   │
│  │  ├── transactions (all balance changes)                              │   │
│  │  ├── deposits (USDC from L1)                                         │   │
│  │  ├── withdrawals (payouts to workers)                                │   │
│  │  ├── epochs (sealed blocks)                                          │   │
│  │  └── settlements (per-worker per-epoch)                              │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   BEE-2     │  │   BEE-3     │  │   BEE-4     │  │   BEE-N     │       │
│  │   Worker    │  │   Worker    │  │   Worker    │  │   Worker    │       │
│  │             │  │             │  │             │  │             │       │
│  │ 8x 5090     │  │ 8x 6000Ada  │  │ 8x 3090     │  │ ...         │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════   │
│                              LAN (10.0.0.x)                                  │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Client Deposit

```
Client (browser)
    │
    │ 1. Connect wallet
    │ 2. Send USDC to vault.swarmledger.eth
    ▼
Ethereum L1
    │
    │ 3. Transaction confirmed
    ▼
SwarmLedger Watcher
    │
    │ 4. Detect deposit
    │ 5. Credit client balance
    ▼
swarmledger.db
    │
    │ accounts[xyz.clientswarm.eth].balance += $50
    │ transactions += DEPOSIT record
    ▼
Client dashboard shows updated balance
```

### 2. Job Execution

```
Client (xyz.clientswarm.eth)
    │
    │ 1. POST /api/v1/jobs (signed)
    ▼
Bee-1 (swarmos.eth)
    │
    │ 2. GET /v1/balances/xyz.clientswarm.eth
    ▼
SwarmLedger
    │
    │ 3. Return balance: $245.00
    ▼
Bee-1
    │
    │ 4. POST /v1/balances/.../reserve ($0.10)
    │ 5. Queue job in Redis
    ▼
Bee-2 (bee-01.swarmbee.eth)
    │
    │ 6. Claim job
    │ 7. Run MONAI inference
    │ 8. Generate PoE hash
    │ 9. POST /api/v1/jobs/{id}/complete
    ▼
Bee-1
    │
    │ 10. POST /v1/balances/.../charge ($0.10)
    │ 11. POST /v1/balances/bee-01.../credit ($0.07, pending)
    ▼
SwarmLedger
    │
    │ accounts[client].balance -= $0.10
    │ accounts[worker].pending += $0.07
    │ transactions += JOB_CHARGE, EARNING (pending)
    ▼
Job complete, client can fetch result
```

### 3. Epoch Settlement

```
Epoch Sealer (cron, every 24h)
    │
    │ 1. Collect completed jobs
    │ 2. Build Merkle tree
    │ 3. Calculate payouts
    ▼
    │
    │ 4. POST /v1/epochs/{id}/seal
    │    {
    │      merkle_root: "7ec20e03...",
    │      jobs_count: 248,
    │      settlements: [
    │        {worker: "bee-01...", earned: "17.36"},
    │        {worker: "bee-02...", earned: "12.84"},
    │      ]
    │    }
    ▼
SwarmLedger
    │
    │ 5. Finalize settlements
    │    accounts[worker].pending → balance
    │    transactions += EARNING (finalized)
    │
    │ 6. Record epoch
    │    epochs[002].status = "finalized"
    │    epochs[002].merkle_root = "7ec20e03..."
    ▼
IPFS
    │
    │ 7. Pin epoch bundle
    │    audit/epoch-002/
    │    ├── SUMMARY.json
    │    ├── jobs.json
    │    ├── agents.json
    │    └── SIGNATURE.txt
    ▼
SwarmOrb
    │
    │ 8. Update index
    │    swarmorb.eth.limo shows new epoch
    ▼
Epoch finalized
```

### 4. Worker Withdrawal

```
Worker (bee-01.swarmbee.eth)
    │
    │ 1. POST /v1/withdrawals
    │    {
    │      amount: "50.00",
    │      destination: "0xABC...",
    │      signature: "0x..."
    │    }
    ▼
SwarmLedger
    │
    │ 2. Verify signature
    │ 3. Check balance
    │ 4. Create withdrawal request
    │ 5. Reserve funds
    ▼
Admin/Automated
    │
    │ 6. Process withdrawal
    │ 7. Send USDC on L1
    ▼
Ethereum L1
    │
    │ 8. Transaction confirmed
    ▼
SwarmLedger
    │
    │ 9. Mark withdrawal complete
    │    accounts[worker].balance -= $50
    │    transactions += PAYOUT record
    ▼
Worker receives USDC
```

## API Endpoints Summary

### Bee-1 Controller (api.swarmos.eth)

```
POST   /api/v1/jobs                    Submit job
GET    /api/v1/jobs/{id}               Job status
GET    /api/v1/jobs/{id}/receipt       Merkle receipt
POST   /api/v1/workers/register        Register worker
POST   /api/v1/workers/heartbeat       Worker heartbeat
POST   /api/v1/jobs/claim              Claim job
POST   /api/v1/jobs/{id}/complete      Complete job
GET    /api/v1/epochs/current          Current epoch
```

### SwarmLedger (api.swarmledger.eth)

```
GET    /v1/balances/{ens}              Get balance
POST   /v1/balances/{ens}/reserve      Reserve funds
POST   /v1/balances/{ens}/charge       Charge funds
POST   /v1/balances/{ens}/credit       Credit earnings
POST   /v1/deposits                    Record deposit
GET    /v1/deposits                    List deposits
POST   /v1/withdrawals                 Request withdrawal
GET    /v1/withdrawals/{id}            Withdrawal status
GET    /v1/transactions                Transaction history
GET    /v1/epochs                      List epochs
POST   /v1/epochs/{id}/seal            Seal epoch
POST   /v1/verify/receipt              Verify receipt
```

## Docker Compose (Full Stack)

```yaml
version: '3.8'

services:
  # Bee-1 Controller
  bee1:
    build: ./swarmos-backend/bee1
    ports: ["8000:8000"]
    environment:
      - LEDGER_URL=http://ledger:8100
      - REDIS_URL=redis://redis:6379/0
    depends_on: [ledger, redis]

  # SwarmLedger
  ledger:
    build: ./swarmledger
    ports: ["8100:8100"]
    volumes:
      - ledger_data:/app/data

  # Redis
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  # IPFS
  ipfs:
    image: ipfs/kubo:latest
    ports: ["5001:5001", "8080:8080"]

  # Bee-2 Workers (add per GPU node)
  bee2-01:
    build: ./swarmos-backend/bee2
    environment:
      - WORKER_ENS=bee-01.swarmbee.eth
      - BEE1_URL=http://bee1:8000
    depends_on: [bee1]

volumes:
  ledger_data:
```

## Deployment Checklist

### Phase 1: Landing Pages ✅
- [x] swarmorb.eth.limo (LIVE)
- [x] swarmos.eth.limo (ready)
- [x] clientswarm.eth.limo (ready)
- [x] swarmledger.eth.limo (ready)

### Phase 2: Backend Services
- [ ] Deploy Bee-1 Controller
- [ ] Deploy SwarmLedger API
- [ ] Deploy Redis
- [ ] Deploy IPFS node
- [ ] Configure DNS/ENS resolution

### Phase 3: Worker Nodes
- [ ] Set up Bee-2 on GPU rack 1 (5090s)
- [ ] Set up Bee-3 on GPU rack 2 (6000 Adas)
- [ ] Set up Bee-4 on GPU rack 3 (3090s)
- [ ] Test job execution flow

### Phase 4: Settlement
- [ ] Configure epoch sealer cron
- [ ] Test epoch settlement flow
- [ ] Verify SwarmOrb integration
- [ ] Test receipt verification

### Phase 5: Payments
- [ ] Set up USDC vault address
- [ ] Deploy deposit watcher
- [ ] Test deposit flow
- [ ] Test withdrawal flow

---

*This is the complete SwarmOS stack. Sovereign compute infrastructure.*

🐝💰⚡
