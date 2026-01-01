#!/bin/bash
# SwarmOrb Snapshot Script
# Captures current Bee-1 state for static IPFS deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORB_UI="$SCRIPT_DIR/../apps/orb-ui"
DATA_DIR="$ORB_UI/public/data/orb"
API_URL="${BEE1_API:-http://localhost:8000}"

echo "SwarmOrb Snapshot"
echo "================="
echo "API: $API_URL"
echo ""

# Check API is reachable
if ! curl -s "$API_URL/v1/stats" > /dev/null 2>&1; then
    echo "ERROR: Cannot reach Bee-1 API at $API_URL"
    exit 1
fi

# Create data directory
mkdir -p "$DATA_DIR"

# Fetch current stats
echo "Fetching stats from Bee-1..."
STATS=$(curl -s "$API_URL/v1/stats")

# Generate live.json
echo "Generating live.json..."
python3 << EOF
import json

stats = json.loads('''$STATS''')

# Find active epoch
epochs = stats.get('epochs', {}).get('list', [])
current = next((e for e in epochs if e.get('status') == 'active'), {})
workers = stats.get('workers', {}).get('list', [])

revenue = stats.get('volume', {}).get('current_epoch_usdc', 0)

live = {
    "version": "1.0.0",
    "timestamp": stats.get('updated_at', ''),
    "coordinator": "bee1.swarmos.eth",
    "current_epoch": {
        "epoch_id": current.get('epoch_id', stats.get('epochs', {}).get('current_id', 'epoch-001')),
        "started_at": current.get('started_at', ''),
        "ends_at": "",
        "jobs_completed": stats.get('jobs', {}).get('current_epoch', 0),
        "jobs_in_progress": stats.get('jobs', {}).get('processing', 0),
        "revenue_collected": f"{revenue:.2f}",
        "work_pool": f"{revenue * 0.70:.2f}",
        "readiness_pool": f"{revenue * 0.30:.2f}"
    },
    "agents": [
        {
            "ens": w.get('ens'),
            "status": w.get('status', 'online'),
            "last_heartbeat": w.get('last_heartbeat', ''),
            "current_job": None,
            "jobs_this_epoch": w.get('jobs_completed', 0),
            "uptime_this_epoch": 86400,
            "hardware": w.get('hardware', {})
        }
        for w in workers
    ],
    "queue": {
        "pending": stats.get('queue', {}).get('spine_pending', 0) +
                   stats.get('queue', {}).get('chest_pending', 0) +
                   stats.get('queue', {}).get('cardiac_pending', 0),
        "in_progress": stats.get('queue', {}).get('processing', 0),
        "avg_wait_seconds": 0
    }
}

with open('$DATA_DIR/live.json', 'w') as f:
    json.dump(live, f, indent=2)

print(f"  Epoch: {live['current_epoch']['epoch_id']}")
print(f"  Jobs: {live['current_epoch']['jobs_completed']}")
print(f"  Revenue: \${revenue:.2f}")
EOF

# Generate index.json
echo "Generating index.json..."
python3 << EOF
import json

stats = json.loads('''$STATS''')

epochs = stats.get('epochs', {}).get('list', [])
workers = stats.get('workers', {}).get('list', [])
sealed = [e for e in epochs if e.get('status') == 'sealed']
total_volume = stats.get('volume', {}).get('total_usdc', 0)

# Build top agents
top_agents = [
    {
        "ens": w.get('ens'),
        "jobs_completed": w.get('jobs_completed', 0),
        "total_earned": f"{w.get('jobs_completed', 0) * 0.093:.2f}",
        "uptime_hours": 24.0
    }
    for w in workers
]

index = {
    "version": "1.0.0",
    "generated_at": stats.get('updated_at', ''),
    "coordinator": "bee1.swarmos.eth",
    "epochs": [
        {
            "epoch_id": e.get('epoch_id'),
            "start_time": e.get('started_at', ''),
            "end_time": e.get('ended_at', ''),
            "status": e.get('status'),
            "bundle_ref": "",
            "summary_hash": e.get('merkle_root', ''),
            "jobs_completed": e.get('jobs_completed', 0),
            "total_distributed": f"{e.get('total_volume_usdc', 0) * 0.93:.2f}",
            "agents_active": stats.get('workers', {}).get('total', 1)
        }
        for e in sealed
    ],
    "stats": {
        "total_epochs": stats.get('epochs', {}).get('total', 1),
        "total_jobs": stats.get('jobs', {}).get('total', 0),
        "total_distributed": f"{total_volume * 0.93:.2f}",
        "unique_agents": stats.get('workers', {}).get('total', 0),
        "unique_clients": 1,
        "top_agents": top_agents
    }
}

with open('$DATA_DIR/index.json', 'w') as f:
    json.dump(index, f, indent=2)

print(f"  Total epochs: {index['stats']['total_epochs']}")
print(f"  Total jobs: {index['stats']['total_jobs']}")
print(f"  Distributed: \${total_volume * 0.93:.2f}")
EOF

echo ""
echo "Snapshot saved to $DATA_DIR/"
echo ""
echo "To deploy:"
echo "  cd $ORB_UI"
echo "  npm run build"
echo "  w3 up dist/ --name swarmorb-snapshot"
