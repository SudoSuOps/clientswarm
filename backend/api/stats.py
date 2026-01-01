"""
Dashboard Stats API
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import get_current_client
from services.database import get_jobs_collection

router = APIRouter(prefix="/stats", tags=["stats"])


class DashboardStats(BaseModel):
    total_jobs: int
    pending_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_spent: float
    avg_confidence: float
    jobs_today: int
    jobs_this_week: int


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(client: dict = Depends(get_current_client)):
    """Get dashboard statistics for current client"""
    jobs = get_jobs_collection()
    wallet = client["wallet"]

    # Aggregation pipeline
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    pipeline = [
        {"$match": {"client_wallet": wallet}},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "pending": {
                    "$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}
                },
                "completed": {
                    "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                },
                "failed": {
                    "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                },
                "total_spent": {"$sum": {"$ifNull": ["$cost", 0]}},
                "avg_confidence": {"$avg": {"$ifNull": ["$confidence", 0]}},
                "jobs_today": {
                    "$sum": {
                        "$cond": [{"$gte": ["$created_at", today_start]}, 1, 0]
                    }
                },
                "jobs_week": {
                    "$sum": {
                        "$cond": [{"$gte": ["$created_at", week_start]}, 1, 0]
                    }
                }
            }
        }
    ]

    result = await jobs.aggregate(pipeline).to_list(1)

    if not result:
        return {
            "total_jobs": 0,
            "pending_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "total_spent": 0.0,
            "avg_confidence": 0.0,
            "jobs_today": 0,
            "jobs_this_week": 0
        }

    stats = result[0]
    return {
        "total_jobs": stats["total"],
        "pending_jobs": stats["pending"],
        "completed_jobs": stats["completed"],
        "failed_jobs": stats["failed"],
        "total_spent": stats["total_spent"],
        "avg_confidence": stats["avg_confidence"] or 0.0,
        "jobs_today": stats["jobs_today"],
        "jobs_this_week": stats["jobs_week"]
    }
