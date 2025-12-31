# SwarmOS Genesis

**December 31, 2025**
**New Year's Eve**

---

## The Moment

Two years of work. Hundreds of GPUs. Thousands of hours.
Solar panels. Battery banks. Rails. Epochs. Bees.

This is not a pitch deck.
This is not a token launch.
This is not a promise.

This is **SwarmOS** — sovereign compute infrastructure that settles in math, not trust.

---

## The Parallel

Bitcoin proved something radical:

> Clean truth can run on real energy.

SHA-256. Mining pools. Miners. Blocks. Rewards. Immutable.

No banks. No middlemen. No trust required.

**SwarmOS extends this idea:**

| Bitcoin | SwarmOS |
|---------|---------|
| SHA-256 | Proof of Execution |
| Mining Pools | SwarmOS Coordinator |
| Miners | Bees (`*.swarmbee.eth`) |
| Blocks | Epochs |
| Block Rewards | Work Pool + Readiness Pool |
| Block Explorer | SwarmOrb |
| Hashrate | GPU Compute |
| Energy (coal/hydro) | Energy (solar/battery) |
| Immutable Ledger | Sealed Epochs + Merkle Roots |

But SwarmOS does something Bitcoin cannot:

> Bitcoin proves you burned energy.
> **SwarmOS proves you did useful work.**

MRI inference. Spine analysis. Medical AI. Real patients. Real outcomes.

---

## The Three Planes

SwarmOS operates across three distinct planes:

### 1. Execution Plane (LOCAL — Sovereign)

This is the real system. It never leaves your network.

```
┌─────────────────────────────────────────────────┐
│              YOUR RACK (LAN ONLY)               │
│                                                 │
│  BEE-1 ──▶ BEE-2 ──▶ BEE-N                     │
│  ingress   MONAI     workers                    │
│  routing   inference  compute                   │
│  ledger                                         │
│  epochs                                         │
│                                                 │
│  RAILS ────▶ LEDGER                            │
│  queues      SQLite                             │
│  settlement  epochs                             │
│                                                 │
│  48x RTX 5090 │ 48x RTX 6000 Ada │ 200x 3090   │
│  SOLAR POWER  │ BATTERY BACKUP                 │
└─────────────────────────────────────────────────┘
```

**This never leaves your network. Ever.**

### 2. Identity Plane (ENS — Cryptographic)

This is how the world names you. No email. No passwords. No OAuth.

| ENS | Function |
|-----|----------|
| `swarmos.eth` | Controller / Queen |
| `bee23.eth` | Law / Protocol |
| `swarmbee.eth` | Workers (`*.swarmbee.eth`) |
| `swarmepoch.eth` | Ledger / Settlement |
| `swarmorb.eth` | Observer / Explorer |
| `swarmbank.eth` | Treasury / Payouts |

ENS is not branding. **ENS is infrastructure identity.**

### 3. Witness Plane (eth.limo — Read-Only)

This is the glass wall. The world can see. They cannot touch.

```
swarmos.eth.limo ────── SwarmOS Dashboard
swarmorb.eth.limo ───── Epoch Explorer (LIVE ✓)
swarmbee.eth.limo ───── Agent Registry
swarmepoch.eth.limo ─── Settlement Proofs
```

Static. Dumb. Unstoppable. Perfect.

---

## The Flow

```
Client (browser via eth.limo)
       │
       ▼ loads static UI from IPFS
       │
       ▼ signs job request with ENS wallet
       │
       │  {
       │    ens: "clinic.swarmos.eth",
       │    job_type: "spine_mri",
       │    epoch: "epoch-002",
       │    nonce: "abc123",
       │    signature: "0x..."
       │  }
       │
       ▼ sends signed payload to Bee-1
       │
Bee-1 (your rack)
       │
       ▼ verifies signature + ENS ownership
       │
       ▼ routes to Bee-2 (LAN only)
       │
       ▼ MONAI inference runs
       │
       ▼ result returns
       │
       ▼ settles job + updates ledger
       │
       ▼ epoch seals with Merkle root
       │
DONE — no cloud touched
```

---

## The Stack

```
bee23.eth
    │
    │   The Law
    │   Immutable protocol rules
    │   What is allowed. What is not.
    │
    ▼
swarmos.eth
    │
    │   The Operating System
    │   Coordination. Routing. Epochs.
    │   The Queen that runs the hive.
    │
    ▼
*.swarmbee.eth
    │
    │   The Bees
    │   Workers. Miners. GPU operators.
    │   They do the work. They get paid.
    │
    ▼
swarmepoch.eth
    │
    │   The Ledger
    │   Sealed epochs. Merkle roots.
    │   Immutable record of compute.
    │
    ▼
swarmorb.eth
    │
    │   The Orb
    │   Eyes on the ecosystem.
    │   Read-only. Verifiable. True.
    │
    ▼
swarmbank.eth
    │
    │   The Treasury
    │   Work Pool (70%). Readiness Pool (30%).
    │   Honest pay for honest compute.
    │
    ▼
SETTLEMENT
```

---

## The Economics

Every epoch (24 hours):

```
Total Revenue ─────────────────────────────▶ 100%
       │
       ├── Work Pool (70%) ────────────────▶ Paid per job completed
       │
       ├── Readiness Pool (30%) ───────────▶ Paid for uptime + availability
       │
       ├── Protocol Fee (2%) ─────────────▶ bee23.eth (law maintenance)
       │
       └── Operator Fee (5%) ─────────────▶ Infrastructure costs
```

**An honest day's compute for an honest day's pay.**

---

## The Moat

| Others | SwarmOS |
|--------|---------|
| Decentralize without control | Own the rack |
| Cloud-host without sovereignty | Own the power |
| Add tokens before truth | Epochs seal math first |
| Auth servers, OAuth, SaaS | ENS signatures only |
| Promise future utility | Deliver current compute |
| Marketing tech | Operator-grade infrastructure |

---

## The Guarantees

### Receipts (v1.1)

Every job gets a cryptographic receipt:

```json
{
  "job_id": "job-001-0001",
  "epoch_id": "epoch-001",
  "leaf_hash": "5aa97d62...",
  "jobs_merkle_root": "7ec20e03...",
  "merkle_proof": [...]
}
```

If the receipt verifies, the job ran. Period.

### Reputation (v1.1)

Agent reputation is not assigned. It is computed.

```
Completion Rate × Availability × (1 - Failure Rate) → Score Band

A+ : Elite (≥99% completion, ≥98% availability)
A  : Reliable
B  : Acceptable
C  : Degraded
D  : Excluded
```

No votes. No staking. No appeals. Only math over history.

---

## The Culture

We are not:
- A token
- A DAO
- A pitch deck
- A promise

We are:
- Real hardware (296 GPUs)
- Real power (solar + battery)
- Real work (medical AI inference)
- Real settlement (epochs seal, math pays)
- Real identity (ENS, no middlemen)

---

## The Doctrine

1. **Verifiability over Decentralization** — A single honest operator with receipts beats a thousand anonymous nodes without them.

2. **Power Proportional to Demand** — Don't run what you can't settle.

3. **Immutability through Sealing** — Once an epoch closes, its truth is fixed.

4. **Minimalism over Bloat** — Every component must justify its existence.

5. **Adoption before Abstraction** — Ship what works. Abstract later.

---

## The Statement

```
The Orb watches.
The Bees work.
The Epochs seal.
The Math pays.

Clean truth runs on real energy,
real hardware, real operating system,
real culture.

An honest day's compute
for an honest day's pay.

Sovereign trust.
```

---

## The Genesis Block

**Epoch-001**

- Date: January 15-16, 2025
- Jobs: 105
- Distributed: $1,247.50
- Agents: 5
- Status: **FINALIZED**
- Merkle Root: `7ec20e03b05b7898c3cdc33f0d066ddf860091338eaace5ad51df1f1f8c472b5`

Witnessed at: [swarmorb.eth.limo](https://swarmorb.eth.limo)

---

## The Signature

```
SwarmOS Genesis
December 31, 2025
New Year's Eve

Signed: SudoHash LLC
        $root.eth
        sudohash.eth
        swarmos.eth

"SwarmOrb exists because claims are cheap and compute is not."
```

---

*This document is the founding record of SwarmOS.*
*Pin it. Sign it. Seal it.*

🧿🐝⚡
