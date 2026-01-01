"""
ClientSwarm Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "ClientSwarm"
    debug: bool = False

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "clientswarm"

    # IPFS
    ipfs_api: str = "http://localhost:5001"
    ipfs_gateway: str = "https://ipfs.io/ipfs"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # SwarmPool
    swarmpool_pool: str = "swarmpool.eth"
    client_private_key: str = ""  # For signing jobs

    # Billing
    free_trial_scans: int = 10
    price_per_scan: float = 0.10

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
