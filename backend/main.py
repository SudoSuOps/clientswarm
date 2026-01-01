"""
ClientSwarm Backend - FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from services.database import Database
from api import auth, jobs, upload, stats, settings as settings_api

config = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await Database.connect()
    yield
    # Shutdown
    await Database.disconnect()


app = FastAPI(
    title="ClientSwarm API",
    description="Client gateway for SwarmPool medical inference network",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://clientswarm.eth.limo"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(upload.router)
app.include_router(stats.router)
app.include_router(settings_api.router)


@app.get("/")
async def root():
    return {
        "name": "ClientSwarm API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
