# SwarmLedger Architecture

## Overview

**swarmledger.eth** is the canonical settlement layer for SwarmOS. It provides:

1. **On-chain anchoring** — Epoch Merkle roots committed to L1
2. **Balance ledger** — Client credit balances and worker earnings
3. **Settlement proofs** — Cryptographic receipts for all transactions
4. **Payment rails** — USDC transfers on Ethereum L1

```
┌─────────────────────────────────────────────────────────────────┐
│                     SWARMLEDGER                                  │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  BALANCES   │  │   EPOCHS    │  │  PAYMENTS   │             │
│  │             │  │             │  │             │             │
│  │ • Clients   │  │ • Roots     │  │ • Deposits  │             │
│  │ • Workers   │  │ • Proofs    │  │ • Payouts   │             │
│  │ • Treasury  │  │ • Hashes    │  │ • History   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ════════════════════════════════════════════════════════════   │
│                     ETHEREUM L1 (USDC)                          │
│  ════════════════════════════════════════════════════════════   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Full Stack Integration

### ENS Identity Map (Complete)

| ENS | Role | Subdomains | eth.limo |
|-----|------|------------|----------|
| `bee23.eth` | Law / Protocol | — | Protocol docs |
| `swarmos.eth` | Controller / Queen | `api.swarmos.eth` | Landing page |
| `swarmbee.eth` | Workers | `bee-01.swarmbee.eth`, etc | Worker registry |
| `clientswarm.eth` | Clients | `xyz.clientswarm.eth`, etc | Client portal |
| `swarmledger.eth` | **Settlement** | `api.swarmledger.eth` | **Ledger explorer** |
| `swarmepoch.eth` | Epoch data | `data.swarmepoch.eth` | Epoch archive |
| `swarmbank.eth` | Treasury | `vault.swarmbank.eth` | Payout dashboard |
| `swarmorb.eth` | Explorer | — | Public explorer |

### Data Flow

```
CLIENT DEPOSIT
══════════════
xyz.clientswarm.eth
       │
       │ 1. Send USDC to swarmledger.eth vault
       ▼
Ethereum L1 (USDC transfer)
       │
       │ 2. Watcher detects deposit
       ▼
SwarmLedger API
       │
       │ 3. Credit client balance
       ▼
Client ready to submit jobs


JOB EXECUTION
═════════════
xyz.clientswarm.eth
       │
       │ 1. Submit job (signed)
       ▼
Bee-1 (swarmos.eth)
       │
       │ 2. Check balance via SwarmLedger API
       │ 3. Reserve funds
       ▼
Bee-2 (*.swarmbee.eth)
       │
       │ 4. Execute inference
       ▼
Bee-1 (swarmos.eth)
       │
       │ 5. Update SwarmLedger
       │    - Deduct client balance
       │    - Credit worker earnings (pending)
       ▼
Job complete, receipt generated


EPOCH SETTLEMENT
════════════════
Epoch Sealer (cron)
       │
       │ 1. Collect all jobs in epoch
       │ 2. Compute Merkle root
       │ 3. Calculate payouts
       ▼
SwarmLedger API
       │
       │ 4. Finalize worker earnings
       │ 5. Record epoch settlement
       ▼
Ethereum L1
       │
       │ 6. Anchor Merkle root on-chain (optional)
       │ 7. Batch payout to workers (if requested)
       ▼
Epoch finalized, SwarmOrb updated
```

---

## SwarmLedger Components

### 1. Balance Ledger

Tracks all account balances off-chain for speed, with on-chain settlement.

```
┌─────────────────────────────────────────────────────────────────┐
│                      BALANCE LEDGER                              │
│                                                                  │
│  CLIENT ACCOUNTS                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  ENS                          Balance    Reserved   Available   │
│  ─────────────────────────────────────────────────────────────  │
│  xyz.clientswarm.eth          $245.00    $10.00     $235.00    │
│  acme.clientswarm.eth         $1,240.00  $0.00      $1,240.00  │
│  metro.clientswarm.eth        $89.50     $5.00      $84.50     │
│                                                                  │
│  WORKER ACCOUNTS                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  ENS                          Earned     Pending    Withdrawn   │
│  ─────────────────────────────────────────────────────────────  │
│  bee-01.swarmbee.eth          $847.30    $45.20     $802.10    │
│  bee-02.swarmbee.eth          $623.15    $38.90     $584.25    │
│  bee-03.swarmbee.eth          $412.80    $22.10     $390.70    │
│                                                                  │
│  TREASURY                                                        │
│  ─────────────────────────────────────────────────────────────  │
│  swarmbank.eth (vault)        $12,450.00                        │
│  Protocol fee (bee23.eth)     $892.30                           │
│  Operator fee (swarmos.eth)   $2,230.75                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Epoch Registry

Stores sealed epoch data with Merkle roots.

```
┌─────────────────────────────────────────────────────────────────┐
│                      EPOCH REGISTRY                              │
│                                                                  │
│  Epoch      Status      Jobs    Revenue     Merkle Root         │
│  ─────────────────────────────────────────────────────────────  │
│  epoch-001  FINALIZED   105     $10.50      7ec20e03b05b...     │
│  epoch-002  FINALIZED   248     $24.80      a3f891c2e7d4...     │
│  epoch-003  ACTIVE      67      $6.70       (pending)           │
│                                                                  │
│  ANCHORED ON-CHAIN                                              │
│  ─────────────────────────────────────────────────────────────  │
│  epoch-001  tx: 0x8a3f...  block: 19234567                      │
│  epoch-002  tx: 0x2b7c...  block: 19241234                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Transaction History

Immutable log of all balance changes.

```
┌─────────────────────────────────────────────────────────────────┐
│                   TRANSACTION HISTORY                            │
│                                                                  │
│  ID          Type        Account                 Amount   Ref   │
│  ─────────────────────────────────────────────────────────────  │
│  tx-00847    DEPOSIT     xyz.clientswarm.eth     +$50.00  0x... │
│  tx-00848    JOB_CHARGE  xyz.clientswarm.eth     -$0.10   job-  │
│  tx-00849    JOB_CHARGE  xyz.clientswarm.eth     -$0.10   job-  │
│  tx-00850    EARNING     bee-01.swarmbee.eth     +$0.07   job-  │
│  tx-00851    PAYOUT      bee-01.swarmbee.eth     -$50.00  0x... │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Smart Contract Design (Optional)

For maximum trustlessness, deploy a simple registry contract:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title SwarmLedger Registry
/// @notice On-chain anchor for epoch settlements
contract SwarmLedgerRegistry {
    
    address public immutable owner;        // swarmos.eth
    address public immutable protocol;     // bee23.eth
    
    struct EpochSeal {
        bytes32 jobsMerkleRoot;
        uint256 jobsCount;
        uint256 totalRevenue;      // In USDC cents
        uint256 sealedAt;
        bytes signature;           // EIP-191 signature
    }
    
    mapping(uint256 => EpochSeal) public epochs;
    uint256 public latestEpoch;
    
    event EpochSealed(
        uint256 indexed epochId,
        bytes32 jobsMerkleRoot,
        uint256 jobsCount,
        uint256 totalRevenue
    );
    
    constructor(address _protocol) {
        owner = msg.sender;
        protocol = _protocol;
    }
    
    /// @notice Seal an epoch by recording its Merkle root
    function sealEpoch(
        uint256 epochId,
        bytes32 jobsMerkleRoot,
        uint256 jobsCount,
        uint256 totalRevenue,
        bytes calldata signature
    ) external {
        require(msg.sender == owner, "Only owner");
        require(epochId == latestEpoch + 1, "Must be sequential");
        
        epochs[epochId] = EpochSeal({
            jobsMerkleRoot: jobsMerkleRoot,
            jobsCount: jobsCount,
            totalRevenue: totalRevenue,
            sealedAt: block.timestamp,
            signature: signature
        });
        
        latestEpoch = epochId;
        
        emit EpochSealed(epochId, jobsMerkleRoot, jobsCount, totalRevenue);
    }
    
    /// @notice Verify a job was included in an epoch
    function verifyJob(
        uint256 epochId,
        bytes32 leafHash,
        bytes32[] calldata proof
    ) external view returns (bool) {
        bytes32 root = epochs[epochId].jobsMerkleRoot;
        return _verifyMerkleProof(proof, root, leafHash);
    }
    
    function _verifyMerkleProof(
        bytes32[] memory proof,
        bytes32 root,
        bytes32 leaf
    ) internal pure returns (bool) {
        bytes32 computedHash = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 proofElement = proof[i];
            if (computedHash <= proofElement) {
                computedHash = keccak256(abi.encodePacked(computedHash, proofElement));
            } else {
                computedHash = keccak256(abi.encodePacked(proofElement, computedHash));
            }
        }
        return computedHash == root;
    }
}
```

**Deployment cost:** ~500k gas (~$15-30 at current prices)
**Per-epoch seal:** ~80k gas (~$2-5)

---

## API Design

### SwarmLedger API (api.swarmledger.eth)

```
BASE URL: https://api.swarmledger.eth.limo/v1
         or https://ledger.swarmos.eth.limo/v1

BALANCES
────────
GET  /balances/{ens}              # Get account balance
POST /balances/{ens}/reserve      # Reserve funds for job
POST /balances/{ens}/charge       # Finalize charge
POST /balances/{ens}/credit       # Credit earnings

DEPOSITS
────────
POST /deposits/watch              # Register deposit to watch
GET  /deposits/{tx_hash}          # Get deposit status
POST /deposits/confirm            # Confirm deposit (internal)

WITHDRAWALS
───────────
POST /withdrawals/request         # Request payout (worker)
GET  /withdrawals/{id}            # Get withdrawal status
POST /withdrawals/process         # Process withdrawal (admin)

EPOCHS
──────
GET  /epochs                      # List all epochs
GET  /epochs/current              # Get current epoch
GET  /epochs/{id}                 # Get epoch details
POST /epochs/{id}/seal            # Seal epoch (internal)
GET  /epochs/{id}/settlements     # Get epoch settlements

TRANSACTIONS
────────────
GET  /transactions?account={ens}  # Transaction history
GET  /transactions/{id}           # Get transaction details

RECEIPTS
────────
GET  /receipts/{job_id}           # Get job receipt
POST /receipts/verify             # Verify receipt
```

---

## Database Schema

```sql
-- =============================================================================
-- SWARMLEDGER DATABASE
-- =============================================================================

-- Account balances (clients + workers)
CREATE TABLE accounts (
    ens TEXT PRIMARY KEY,
    account_type TEXT NOT NULL,  -- 'client' | 'worker' | 'treasury'
    balance_usd DECIMAL(12,2) DEFAULT 0,
    reserved_usd DECIMAL(12,2) DEFAULT 0,  -- Pending charges (clients)
    pending_usd DECIMAL(12,2) DEFAULT 0,   -- Pending earnings (workers)
    total_in_usd DECIMAL(12,2) DEFAULT 0,  -- Total deposited/earned
    total_out_usd DECIMAL(12,2) DEFAULT 0, -- Total spent/withdrawn
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- All balance-changing transactions
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,          -- tx-00001
    account_ens TEXT NOT NULL,
    tx_type TEXT NOT NULL,        -- DEPOSIT, JOB_CHARGE, EARNING, PAYOUT, REFUND
    amount_usd DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2) NOT NULL,
    reference_type TEXT,          -- 'job' | 'epoch' | 'eth_tx'
    reference_id TEXT,            -- job-002-0847 | epoch-002 | 0x...
    eth_tx_hash TEXT,             -- L1 tx hash if applicable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_ens) REFERENCES accounts(ens)
);

-- USDC deposits from L1
CREATE TABLE deposits (
    id TEXT PRIMARY KEY,
    client_ens TEXT NOT NULL,
    amount_usd DECIMAL(12,2) NOT NULL,
    eth_tx_hash TEXT NOT NULL UNIQUE,
    block_number INTEGER,
    status TEXT DEFAULT 'pending', -- pending, confirmed, failed
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_ens) REFERENCES accounts(ens)
);

-- Worker payout requests
CREATE TABLE withdrawals (
    id TEXT PRIMARY KEY,
    worker_ens TEXT NOT NULL,
    amount_usd DECIMAL(12,2) NOT NULL,
    destination_address TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    eth_tx_hash TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_ens) REFERENCES accounts(ens)
);

-- Sealed epochs
CREATE TABLE epochs (
    id TEXT PRIMARY KEY,          -- epoch-001
    status TEXT DEFAULT 'active', -- active, sealing, finalized
    jobs_count INTEGER DEFAULT 0,
    jobs_merkle_root TEXT,
    total_revenue_usd DECIMAL(12,2) DEFAULT 0,
    work_pool_usd DECIMAL(12,2) DEFAULT 0,
    readiness_pool_usd DECIMAL(12,2) DEFAULT 0,
    protocol_fee_usd DECIMAL(12,2) DEFAULT 0,
    operator_fee_usd DECIMAL(12,2) DEFAULT 0,
    signature TEXT,               -- EIP-191 signature
    ipfs_hash TEXT,
    eth_tx_hash TEXT,             -- On-chain anchor tx
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    sealed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Per-worker settlements per epoch
CREATE TABLE settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id TEXT NOT NULL,
    worker_ens TEXT NOT NULL,
    jobs_completed INTEGER DEFAULT 0,
    uptime_seconds INTEGER DEFAULT 0,
    work_share_usd DECIMAL(12,2) DEFAULT 0,
    readiness_share_usd DECIMAL(12,2) DEFAULT 0,
    total_earned_usd DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (epoch_id) REFERENCES epochs(id),
    FOREIGN KEY (worker_ens) REFERENCES accounts(ens),
    UNIQUE(epoch_id, worker_ens)
);

-- Indexes
CREATE INDEX idx_transactions_account ON transactions(account_ens);
CREATE INDEX idx_transactions_type ON transactions(tx_type);
CREATE INDEX idx_deposits_status ON deposits(status);
CREATE INDEX idx_withdrawals_status ON withdrawals(status);
CREATE INDEX idx_settlements_epoch ON settlements(epoch_id);
CREATE INDEX idx_settlements_worker ON settlements(worker_ens);
```

---

## Integration with Existing Stack

### Bee-1 → SwarmLedger

```python
# In Bee-1 controller, replace in-memory balance tracking:

class LedgerClient:
    """Client for SwarmLedger API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)
    
    async def get_balance(self, ens: str) -> Decimal:
        """Get available balance for account."""
        resp = await self.client.get(f"/v1/balances/{ens}")
        data = resp.json()
        return Decimal(data["available_usd"])
    
    async def reserve_funds(self, ens: str, amount: Decimal, job_id: str) -> bool:
        """Reserve funds for a pending job."""
        resp = await self.client.post(
            f"/v1/balances/{ens}/reserve",
            json={"amount_usd": str(amount), "job_id": job_id}
        )
        return resp.status_code == 200
    
    async def charge_job(self, ens: str, amount: Decimal, job_id: str) -> bool:
        """Finalize charge after job completion."""
        resp = await self.client.post(
            f"/v1/balances/{ens}/charge",
            json={"amount_usd": str(amount), "job_id": job_id}
        )
        return resp.status_code == 200
    
    async def credit_worker(self, ens: str, amount: Decimal, job_id: str) -> bool:
        """Credit worker earnings (pending until epoch settles)."""
        resp = await self.client.post(
            f"/v1/balances/{ens}/credit",
            json={"amount_usd": str(amount), "job_id": job_id, "pending": True}
        )
        return resp.status_code == 200
```

### Epoch Sealer → SwarmLedger

```python
# In epoch sealer, integrate with ledger:

async def seal_epoch(epoch_id: str, ledger: LedgerClient):
    """Seal epoch and record in SwarmLedger."""
    
    # 1. Get all completed jobs
    jobs = await get_epoch_jobs(epoch_id)
    
    # 2. Build Merkle tree
    merkle = MerkleTree(jobs)
    
    # 3. Calculate settlements
    settlements = calculate_settlements(jobs)
    
    # 4. Sign epoch
    signature = sign_epoch(
        epoch_id=epoch_id,
        merkle_root=merkle.root,
        jobs_count=len(jobs),
        ...
    )
    
    # 5. Record in SwarmLedger
    await ledger.seal_epoch(
        epoch_id=epoch_id,
        jobs_merkle_root=merkle.root,
        jobs_count=len(jobs),
        total_revenue=sum(j["fee_usd"] for j in jobs),
        settlements=settlements,
        signature=signature,
    )
    
    # 6. Finalize worker earnings (move from pending to available)
    for s in settlements:
        await ledger.finalize_earnings(s["worker_ens"], epoch_id)
    
    # 7. Optionally anchor on-chain
    if ANCHOR_ON_CHAIN:
        tx_hash = await anchor_epoch_onchain(epoch_id, merkle.root)
        await ledger.record_anchor(epoch_id, tx_hash)
```

### ClientSwarm Dashboard → SwarmLedger

```javascript
// In client dashboard, fetch balance from ledger API:

async function fetchBalance(clientEns) {
    const resp = await fetch(
        `https://api.swarmledger.eth.limo/v1/balances/${clientEns}`
    );
    const data = await resp.json();
    
    return {
        balance: data.balance_usd,
        reserved: data.reserved_usd,
        available: data.available_usd,
        scansAvailable: Math.floor(data.available_usd / 0.10),
    };
}

async function fetchTransactionHistory(clientEns) {
    const resp = await fetch(
        `https://api.swarmledger.eth.limo/v1/transactions?account=${clientEns}`
    );
    return resp.json();
}
```

---

## SwarmLedger Landing Page

**swarmledger.eth.limo** should show:

1. **Total settled** — All-time USDC settled through the system
2. **Active balances** — Total client deposits, worker earnings
3. **Epoch history** — List of sealed epochs with Merkle roots
4. **Recent transactions** — Live feed of deposits/charges/payouts
5. **Verification tool** — Verify any receipt against epoch Merkle root

---

## Directory Structure

```
swarmledger/
├── ARCHITECTURE.md
├── api/
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── balances.py      # Balance operations
│   │   ├── deposits.py      # Deposit watching
│   │   ├── withdrawals.py   # Worker payouts
│   │   ├── epochs.py        # Epoch management
│   │   └── transactions.py  # Transaction history
│   ├── services/
│   │   ├── ledger.py        # Core ledger logic
│   │   ├── watcher.py       # L1 deposit watcher
│   │   └── settler.py       # Epoch settlement
│   └── deps.py
├── db/
│   ├── models.py            # SQLAlchemy models
│   └── migrations/
├── contracts/
│   └── SwarmLedgerRegistry.sol
├── landing/
│   └── index.html           # swarmledger.eth.limo
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETE SWARMOS FLOW                               │
│                                                                              │
│  1. CLIENT ONBOARDS                                                          │
│     xyz.clientswarm.eth                                                      │
│         │                                                                    │
│         │ Sends $50 USDC to swarmledger.eth vault                           │
│         ▼                                                                    │
│     SwarmLedger detects deposit → credits balance                           │
│                                                                              │
│  2. CLIENT SUBMITS JOB                                                       │
│     xyz.clientswarm.eth                                                      │
│         │                                                                    │
│         │ POST /api/v1/jobs (signed)                                        │
│         ▼                                                                    │
│     Bee-1 (swarmos.eth)                                                     │
│         │                                                                    │
│         ├─► SwarmLedger: reserve $0.10                                      │
│         ├─► Queue job                                                        │
│         ▼                                                                    │
│     Return job_id                                                            │
│                                                                              │
│  3. WORKER EXECUTES                                                          │
│     bee-01.swarmbee.eth                                                      │
│         │                                                                    │
│         │ Claims job from queue                                             │
│         │ Runs MONAI inference                                              │
│         │ Returns result + PoE                                              │
│         ▼                                                                    │
│     Bee-1 (swarmos.eth)                                                     │
│         │                                                                    │
│         ├─► SwarmLedger: charge client $0.10                                │
│         ├─► SwarmLedger: credit worker $0.07 (pending)                      │
│         ▼                                                                    │
│     Job complete                                                             │
│                                                                              │
│  4. EPOCH SEALS (every 24h)                                                  │
│     Epoch Sealer                                                             │
│         │                                                                    │
│         ├─► Compute Merkle root                                             │
│         ├─► Calculate settlements                                           │
│         ├─► SwarmLedger: seal epoch                                         │
│         ├─► SwarmLedger: finalize worker earnings                           │
│         ├─► (Optional) Anchor Merkle root on-chain                          │
│         ├─► Pin to IPFS                                                     │
│         ▼                                                                    │
│     SwarmOrb: update index                                                   │
│                                                                              │
│  5. WORKER WITHDRAWS                                                         │
│     bee-01.swarmbee.eth                                                      │
│         │                                                                    │
│         │ Request payout via SwarmLedger                                    │
│         ▼                                                                    │
│     SwarmLedger                                                              │
│         │                                                                    │
│         ├─► Verify available balance                                        │
│         ├─► Queue USDC transfer                                             │
│         ├─► Execute L1 transaction                                          │
│         ▼                                                                    │
│     Worker receives USDC on L1                                              │
│                                                                              │
│  6. VERIFICATION                                                             │
│     Anyone                                                                   │
│         │                                                                    │
│         │ Fetch receipt from SwarmOrb                                       │
│         │ Verify Merkle proof against epoch root                            │
│         │ (Optional) Verify on-chain anchor                                 │
│         ▼                                                                    │
│     Cryptographic proof of execution                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Plan

### Phase 1: Off-chain Ledger (Now)
- Deploy SwarmLedger API
- Integrate with Bee-1
- Manual USDC deposits/payouts
- swarmledger.eth.limo landing

### Phase 2: Deposit Automation (Next)
- L1 deposit watcher
- Auto-credit on confirmed deposits
- Client-facing deposit flow

### Phase 3: On-chain Anchoring (Later)
- Deploy SwarmLedgerRegistry contract
- Anchor epoch Merkle roots
- Full on-chain verification

### Phase 4: Automated Payouts (Future)
- Batch payout smart contract
- Worker withdrawal requests
- Automated L1 transfers

---

## Security Model

| Layer | Implementation |
|-------|----------------|
| Auth | EIP-191 signatures for all operations |
| Identity | ENS subdomains (client owns key) |
| Deposits | USDC transfers to vault address |
| Payouts | Signed withdrawal requests |
| Epochs | Merkle roots + EIP-191 signatures |
| Verification | Anyone can verify receipts |

---

*SwarmLedger is the spine of SwarmOS. Every dollar flows through here.*

🐝💰⚡
