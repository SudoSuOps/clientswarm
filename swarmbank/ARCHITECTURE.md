# SwarmBank Architecture

## Overview

**swarmbank.eth** is the treasury of SwarmOS. It manages the USDC vault on Ethereum L1, processes deposits, and executes worker payouts.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SWARMBANK                                 │
│                                                                  │
│   The Vault. The Treasury. The Payout Engine.                   │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                      USDC VAULT                          │  │
│   │                                                          │  │
│   │              ┌─────────────────────┐                    │  │
│   │              │                     │                    │  │
│   │    IN ──────►│    $12,847.50      │──────► OUT         │  │
│   │   Deposits   │      USDC          │    Payouts         │  │
│   │              │                     │                    │  │
│   │              └─────────────────────┘                    │  │
│   │                                                          │  │
│   │  0x742d35Cc6634C0532925a3b844Bc9e7595f7e3e0             │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Money Flow

### Inflow: Client Deposits

```
Client Wallet
      │
      │ 1. Send USDC to vault address
      ▼
Ethereum L1
      │
      │ 2. Transaction confirmed
      ▼
SwarmBank Watcher
      │
      │ 3. Detect deposit event
      │ 4. Verify amount
      ▼
SwarmLedger
      │
      │ 5. Credit client balance
      ▼
Client can submit jobs
```

### Outflow: Worker Payouts

```
Worker (via SwarmLedger)
      │
      │ 1. Request withdrawal
      ▼
SwarmBank API
      │
      │ 2. Verify balance in SwarmLedger
      │ 3. Create payout request
      ▼
Payout Processor
      │
      │ 4. Sign L1 transaction
      │ 5. Submit to network
      ▼
Ethereum L1
      │
      │ 6. Transaction confirmed
      ▼
Worker receives USDC
```

---

## Revenue Distribution

Every epoch, revenue is distributed according to:

```
┌─────────────────────────────────────────────────────────────────┐
│                    EPOCH REVENUE: $24.80                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │████████████████████████████████████████████████████░░░░░░░░││
│  │           70% Work Pool                    │23% Ready│ 7%  ││
│  │              $17.36                        │  $5.70  │Fees ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  WORK POOL (70%)          → Distributed per job completed      │
│  READINESS POOL (23%)     → Distributed per uptime             │
│  PROTOCOL FEE (2%)        → bee23.eth                          │
│  OPERATOR FEE (5%)        → swarmos.eth                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Distribution Formula

```python
def calculate_distribution(epoch_revenue: Decimal) -> dict:
    # Fees first
    protocol_fee = epoch_revenue * Decimal("0.02")  # 2%
    operator_fee = epoch_revenue * Decimal("0.05")  # 5%
    
    # Remaining to pools
    remaining = epoch_revenue - protocol_fee - operator_fee  # 93%
    
    # Pool split
    work_pool = remaining * Decimal("0.7526")      # 70% of original
    readiness_pool = remaining * Decimal("0.2474") # 23% of original
    
    return {
        "work_pool": work_pool,
        "readiness_pool": readiness_pool,
        "protocol_fee": protocol_fee,
        "operator_fee": operator_fee,
    }
```

---

## API Endpoints

### Vault Status

```
GET /v1/vault                    # Vault balance and status
GET /v1/stats                    # Treasury statistics
```

### Deposits

```
GET  /v1/deposits                # List all deposits
GET  /v1/deposits/{id}           # Get specific deposit
POST /v1/deposits/watch          # Register deposit to watch
```

### Payouts

```
GET  /v1/payouts                 # List all payouts
GET  /v1/payouts/{id}            # Get specific payout
POST /v1/payouts/request         # Request worker payout
POST /v1/payouts/{id}/process    # Mark as processed (internal)
```

### Treasury

```
GET /v1/treasury/report          # Revenue allocation report
GET /v1/treasury/allocations     # Fee percentages
GET /v1/treasury/recipients      # Fee recipient addresses
```

### Workers

```
GET /v1/workers/{ens}/balance    # Worker's available balance
```

### Integration

```
POST /v1/epochs/{id}/settle      # Settle an epoch
```

---

## Database Schema

```sql
-- =============================================================================
-- SWARMBANK DATABASE
-- =============================================================================

-- USDC deposits from clients
CREATE TABLE deposits (
    id TEXT PRIMARY KEY,              -- dep-00001
    client_ens TEXT NOT NULL,
    amount_usd DECIMAL(12,2) NOT NULL,
    eth_tx_hash TEXT NOT NULL UNIQUE,
    block_number INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',    -- pending, confirmed, failed
    created_at TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP,
    
    INDEX idx_deposits_client (client_ens),
    INDEX idx_deposits_status (status),
    INDEX idx_deposits_tx (eth_tx_hash)
);

-- Worker payouts
CREATE TABLE payouts (
    id TEXT PRIMARY KEY,              -- pay-00001
    worker_ens TEXT NOT NULL,
    amount_usd DECIMAL(12,2) NOT NULL,
    destination_address TEXT NOT NULL,
    status TEXT DEFAULT 'pending',    -- pending, processing, completed, failed
    eth_tx_hash TEXT,
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,
    error_message TEXT,
    
    INDEX idx_payouts_worker (worker_ens),
    INDEX idx_payouts_status (status)
);

-- Epoch settlements
CREATE TABLE settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id TEXT NOT NULL UNIQUE,
    total_revenue_usd DECIMAL(12,2) NOT NULL,
    work_pool_usd DECIMAL(12,2) NOT NULL,
    readiness_pool_usd DECIMAL(12,2) NOT NULL,
    protocol_fee_usd DECIMAL(12,2) NOT NULL,
    operator_fee_usd DECIMAL(12,2) NOT NULL,
    settled_at TIMESTAMP NOT NULL,
    
    INDEX idx_settlements_epoch (epoch_id)
);

-- Vault balance snapshots
CREATE TABLE vault_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    balance_usd DECIMAL(12,2) NOT NULL,
    snapshot_at TIMESTAMP NOT NULL,
    
    INDEX idx_snapshots_time (snapshot_at)
);
```

---

## L1 Integration

### USDC Contract

```
Network: Ethereum Mainnet
Contract: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
Decimals: 6
```

### Deposit Detection

```python
# Watch for USDC transfers to vault
async def watch_deposits():
    usdc = web3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
    
    # Filter for Transfer events to vault
    transfer_filter = usdc.events.Transfer.create_filter(
        fromBlock='latest',
        argument_filters={'to': VAULT_ADDRESS}
    )
    
    while True:
        events = transfer_filter.get_new_entries()
        for event in events:
            await process_deposit(
                from_address=event['args']['from'],
                amount=event['args']['value'],
                tx_hash=event['transactionHash'].hex(),
                block_number=event['blockNumber'],
            )
        await asyncio.sleep(12)  # ~1 block
```

### Payout Execution

```python
async def execute_payout(payout: dict):
    # Build USDC transfer transaction
    usdc = web3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
    
    amount_wei = int(Decimal(payout['amount_usd']) * 10**6)  # 6 decimals
    
    tx = usdc.functions.transfer(
        payout['destination_address'],
        amount_wei
    ).build_transaction({
        'from': VAULT_ADDRESS,
        'gas': 100000,
        'nonce': web3.eth.get_transaction_count(VAULT_ADDRESS),
    })
    
    # Sign with vault key
    signed = web3.eth.account.sign_transaction(tx, VAULT_PRIVATE_KEY)
    
    # Submit
    tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
    
    # Wait for confirmation
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    
    return tx_hash.hex()
```

---

## Security

| Layer | Implementation |
|-------|----------------|
| Vault Key | Hardware wallet / HSM |
| Deposits | Verify L1 confirmation (6+ blocks) |
| Payouts | Require signed withdrawal request |
| Auth | EIP-191 signatures on all operations |
| Rate Limits | Max payout per request, daily limits |
| Monitoring | Real-time vault balance alerts |

### Payout Safeguards

```python
# Maximum single payout
MAX_PAYOUT_USD = Decimal("1000.00")

# Minimum vault reserve
MIN_VAULT_RESERVE_USD = Decimal("1000.00")

# Daily payout limit per worker
DAILY_PAYOUT_LIMIT_USD = Decimal("2000.00")
```

---

## Integration Map

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  CLIENT DEPOSITS                                                │
│       │                                                          │
│       ▼                                                          │
│  SwarmBank (watch) ──────► SwarmLedger (credit balance)         │
│                                                                  │
│  JOB EXECUTION                                                  │
│       │                                                          │
│       ▼                                                          │
│  SwarmLedger (track earnings)                                   │
│                                                                  │
│  EPOCH SETTLEMENT                                               │
│       │                                                          │
│       ▼                                                          │
│  SwarmBank (calculate) ──► SwarmLedger (finalize balances)      │
│       │                                                          │
│       ▼                                                          │
│  SwarmEpoch (archive)                                           │
│                                                                  │
│  WORKER PAYOUT                                                  │
│       │                                                          │
│       ▼                                                          │
│  SwarmLedger (verify) ──► SwarmBank (execute L1 transfer)       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
swarmbank/
├── ARCHITECTURE.md
├── landing/
│   └── index.html           # swarmbank.eth.limo
├── api/
│   ├── main.py              # FastAPI application
│   ├── routes/
│   │   ├── vault.py         # Vault endpoints
│   │   ├── deposits.py      # Deposit management
│   │   ├── payouts.py       # Payout management
│   │   └── treasury.py      # Treasury reports
│   ├── services/
│   │   ├── watcher.py       # L1 deposit watcher
│   │   ├── executor.py      # Payout executor
│   │   └── settler.py       # Epoch settlement
│   └── db/
│       └── models.py        # SQLAlchemy models
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Deployment

### Environment Variables

```bash
# Vault
VAULT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc9e7595f7e3e0
VAULT_PRIVATE_KEY=0x...  # HSM in production

# Ethereum
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/...
USDC_CONTRACT=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48

# Fee recipients
PROTOCOL_FEE_ADDRESS=bee23.eth
OPERATOR_FEE_ADDRESS=swarmos.eth

# Services
SWARMLEDGER_URL=http://ledger:8100
DATABASE_URL=sqlite:///./bank.db
```

### Docker Compose

```yaml
version: '3.8'

services:
  swarmbank:
    build: .
    ports:
      - "8400:8400"
    environment:
      - VAULT_ADDRESS=${VAULT_ADDRESS}
      - ETH_RPC_URL=${ETH_RPC_URL}
      - SWARMLEDGER_URL=http://ledger:8100
    volumes:
      - bank_data:/app/data
    depends_on:
      - ledger

  watcher:
    build: .
    command: python -m api.services.watcher
    environment:
      - ETH_RPC_URL=${ETH_RPC_URL}
      - VAULT_ADDRESS=${VAULT_ADDRESS}

volumes:
  bank_data:
```

---

## Complete Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    SWARMOS FULL STACK                           │
│                                                                  │
│  bee23.eth ──────────────────── Protocol (The Law)             │
│       │                                                          │
│  swarmos.eth ────────────────── Controller (Bee-1)             │
│       │                                                          │
│  swarmbee.eth ───────────────── Workers (Bee-2...N)            │
│       │                                                          │
│  clientswarm.eth ────────────── Clients (Clinics)              │
│       │                                                          │
│  swarmledger.eth ────────────── Settlement Layer               │
│       │                                                          │
│  swarmepoch.eth ─────────────── Epoch Archive                  │
│       │                                                          │
│  swarmbank.eth ──────────────── Treasury ⭐ COMPLETE           │
│       │                                                          │
│  swarmorb.eth ───────────────── Explorer                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*The bank is the heart. Every dollar flows through here.*

🏦💰⚡
