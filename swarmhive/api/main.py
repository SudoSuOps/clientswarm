"""
SwarmHive API

Model Registry for SwarmOS.

Provides:
- Model catalog
- Weight locations
- Performance benchmarks
- Infrastructure status
"""

import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =============================================================================
# Configuration
# =============================================================================

class Config:
    HOST: str = os.getenv("SWARMHIVE_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SWARMHIVE_PORT", "8500"))
    ENS: str = "swarmhive.eth"
    VERSION: str = "1.0.0"


config = Config()


# =============================================================================
# Schemas
# =============================================================================

class ModelSpecs(BaseModel):
    vram_gb: int
    inference_seconds: float
    input_formats: list[str]
    output_formats: list[str]


class ModelPerformance(BaseModel):
    accuracy: float
    sensitivity: float | None = None
    specificity: float | None = None
    auc_roc: float | None = None
    training_samples: int


class ModelWeights(BaseModel):
    huggingface: str | None = None
    ipfs: str | None = None
    container: str


class ModelCard(BaseModel):
    id: str
    name: str
    version: str
    status: str  # production, beta, research
    category: str  # medical, llm, vision
    architecture: str
    description: str
    capabilities: list[str]
    specs: ModelSpecs
    performance: ModelPerformance
    weights: ModelWeights
    license: str


# =============================================================================
# Model Catalog
# =============================================================================

MODELS = {
    # Medical Imaging Models
    "queenbee-spine": {
        "id": "queenbee-spine",
        "name": "QueenBee-Spine",
        "version": "2.1.0",
        "status": "production",
        "category": "medical",
        "architecture": "MONAI SwinUNETR",
        "description": "Lumbar MRI stenosis classification with multi-level analysis and clinical report generation.",
        "capabilities": [
            "stenosis_grading",
            "foraminal_analysis",
            "central_canal_analysis",
            "report_generation"
        ],
        "specs": {
            "vram_gb": 24,
            "inference_seconds": 2.8,
            "input_formats": ["dicom", "nifti", "png_series"],
            "output_formats": ["json", "pdf"]
        },
        "performance": {
            "accuracy": 0.942,
            "sensitivity": 0.938,
            "specificity": 0.947,
            "auc_roc": 0.97,
            "training_samples": 10000
        },
        "weights": {
            "huggingface": "sudohash/queenbee-spine-v2.1",
            "ipfs": "ipfs://QmSpineWeightsHash",
            "container": "swarmos/queenbee-spine:v2.1"
        },
        "license": "proprietary"
    },
    
    "queenbee-foot": {
        "id": "queenbee-foot",
        "name": "QueenBee-Foot",
        "version": "1.8.0",
        "status": "production",
        "category": "medical",
        "architecture": "MONAI DenseNet121",
        "description": "Foot and ankle pathology detection including fractures, arthritis, and soft tissue abnormalities.",
        "capabilities": [
            "fracture_detection",
            "arthritis_classification",
            "soft_tissue_analysis",
            "alignment_analysis"
        ],
        "specs": {
            "vram_gb": 16,
            "inference_seconds": 1.9,
            "input_formats": ["dicom", "png"],
            "output_formats": ["json", "visualization"]
        },
        "performance": {
            "accuracy": 0.917,
            "sensitivity": 0.902,
            "specificity": 0.931,
            "auc_roc": 0.95,
            "training_samples": 8000
        },
        "weights": {
            "huggingface": "sudohash/queenbee-foot-v1.8",
            "ipfs": "ipfs://QmFootWeightsHash",
            "container": "swarmos/queenbee-foot:v1.8"
        },
        "license": "proprietary"
    },
    
    "queenbee-chest": {
        "id": "queenbee-chest",
        "name": "QueenBee-Chest",
        "version": "2.0.0",
        "status": "production",
        "category": "medical",
        "architecture": "MONAI Vision Transformer",
        "description": "Chest X-ray and CT analysis for nodules, pneumonia, cardiomegaly, and multi-finding classification.",
        "capabilities": [
            "nodule_detection",
            "pneumonia_classification",
            "cardiomegaly_detection",
            "pleural_effusion",
            "multi_finding"
        ],
        "specs": {
            "vram_gb": 24,
            "inference_seconds": 2.4,
            "input_formats": ["dicom", "png"],
            "output_formats": ["json", "heatmap"]
        },
        "performance": {
            "accuracy": 0.931,
            "sensitivity": 0.924,
            "specificity": 0.938,
            "auc_roc": 0.96,
            "training_samples": 12000
        },
        "weights": {
            "huggingface": "sudohash/queenbee-chest-v2.0",
            "ipfs": "ipfs://QmChestWeightsHash",
            "container": "swarmos/queenbee-chest:v2.0"
        },
        "license": "proprietary"
    },
    
    "queenbee-brain": {
        "id": "queenbee-brain",
        "name": "QueenBee-Brain",
        "version": "0.9.0",
        "status": "beta",
        "category": "medical",
        "architecture": "MONAI 3D UNet",
        "description": "Brain MRI segmentation for tumor detection, lesion quantification, and volumetric analysis.",
        "capabilities": [
            "tumor_detection",
            "lesion_quantification",
            "volumetric_analysis",
            "wmh_detection"
        ],
        "specs": {
            "vram_gb": 32,
            "inference_seconds": 4.2,
            "input_formats": ["dicom", "nifti"],
            "output_formats": ["nifti_mask", "json"]
        },
        "performance": {
            "accuracy": 0.894,
            "sensitivity": 0.878,
            "specificity": 0.910,
            "auc_roc": 0.93,
            "training_samples": 5000
        },
        "weights": {
            "huggingface": "sudohash/queenbee-brain-v0.9",
            "container": "swarmos/queenbee-brain:v0.9"
        },
        "license": "research"
    },
    
    "queenbee-knee": {
        "id": "queenbee-knee",
        "name": "QueenBee-Knee",
        "version": "0.8.0",
        "status": "beta",
        "category": "medical",
        "architecture": "MONAI ResNet50",
        "description": "Knee MRI analysis for ACL/MCL tears, meniscus pathology, and cartilage grading.",
        "capabilities": [
            "acl_tear_detection",
            "meniscus_analysis",
            "cartilage_grading",
            "bone_edema_detection"
        ],
        "specs": {
            "vram_gb": 24,
            "inference_seconds": 3.1,
            "input_formats": ["dicom", "nifti"],
            "output_formats": ["json", "report"]
        },
        "performance": {
            "accuracy": 0.882,
            "sensitivity": 0.865,
            "specificity": 0.899,
            "auc_roc": 0.92,
            "training_samples": 4000
        },
        "weights": {
            "huggingface": "sudohash/queenbee-knee-v0.8",
            "container": "swarmos/queenbee-knee:v0.8"
        },
        "license": "research"
    },
    
    "queenbee-shoulder": {
        "id": "queenbee-shoulder",
        "name": "QueenBee-Shoulder",
        "version": "0.5.0",
        "status": "research",
        "category": "medical",
        "architecture": "MONAI 3D CNN",
        "description": "Shoulder MRI rotator cuff analysis and muscle atrophy grading.",
        "capabilities": [
            "rotator_cuff_tear",
            "muscle_atrophy_grading",
            "labral_pathology"
        ],
        "specs": {
            "vram_gb": 24,
            "inference_seconds": 3.5,
            "input_formats": ["dicom"],
            "output_formats": ["json"]
        },
        "performance": {
            "accuracy": 0.851,
            "training_samples": 2000
        },
        "weights": {
            "container": "swarmos/queenbee-shoulder:v0.5"
        },
        "license": "research"
    },
    
    # LLMs
    "med42-70b": {
        "id": "med42-70b",
        "name": "Med42-v2",
        "version": "2.0.0",
        "status": "production",
        "category": "llm",
        "architecture": "Llama 2 70B Fine-tuned",
        "description": "Clinical-grade medical LLM for report generation, differential diagnosis, and medical reasoning.",
        "capabilities": [
            "report_generation",
            "differential_diagnosis",
            "medical_reasoning",
            "literature_synthesis"
        ],
        "specs": {
            "vram_gb": 140,
            "inference_seconds": 0.025,  # per token
            "input_formats": ["text"],
            "output_formats": ["text"]
        },
        "performance": {
            "accuracy": 0.89,  # on medical benchmarks
            "training_samples": 1000000
        },
        "weights": {
            "huggingface": "m42-health/med42-70b",
            "container": "swarmos/med42:v2"
        },
        "license": "llama2"
    },
    
    "qwq-32b": {
        "id": "qwq-32b",
        "name": "QwQ",
        "version": "1.0.0",
        "status": "production",
        "category": "llm",
        "architecture": "Qwen 32B",
        "description": "Reasoning-focused LLM for chain-of-thought analysis and complex problem solving.",
        "capabilities": [
            "chain_of_thought",
            "multi_step_reasoning",
            "diagnostic_chains"
        ],
        "specs": {
            "vram_gb": 48,
            "inference_seconds": 0.015,
            "input_formats": ["text"],
            "output_formats": ["text"]
        },
        "performance": {
            "accuracy": 0.87,
            "training_samples": 500000
        },
        "weights": {
            "huggingface": "Qwen/QwQ-32B-Preview",
            "container": "swarmos/qwq:v1"
        },
        "license": "apache2"
    },
    
    "qwen25-72b": {
        "id": "qwen25-72b",
        "name": "Qwen2.5",
        "version": "2.5.0",
        "status": "production",
        "category": "llm",
        "architecture": "Qwen 72B",
        "description": "State-of-the-art general purpose LLM with 128K context and multilingual support.",
        "capabilities": [
            "multilingual",
            "long_context",
            "code_generation",
            "analysis"
        ],
        "specs": {
            "vram_gb": 150,
            "inference_seconds": 0.028,
            "input_formats": ["text"],
            "output_formats": ["text"]
        },
        "performance": {
            "accuracy": 0.91,
            "training_samples": 2000000
        },
        "weights": {
            "huggingface": "Qwen/Qwen2.5-72B-Instruct",
            "container": "swarmos/qwen25:v2.5"
        },
        "license": "apache2"
    },
    
    "mistral-large-123b": {
        "id": "mistral-large-123b",
        "name": "Mistral-Large",
        "version": "1.0.0",
        "status": "production",
        "category": "llm",
        "architecture": "Mistral 123B",
        "description": "European frontier model with strong reasoning and instruction following.",
        "capabilities": [
            "instruction_following",
            "reasoning",
            "code_generation",
            "enterprise_tasks"
        ],
        "specs": {
            "vram_gb": 200,
            "inference_seconds": 0.035,
            "input_formats": ["text"],
            "output_formats": ["text"]
        },
        "performance": {
            "accuracy": 0.92,
            "training_samples": 3000000
        },
        "weights": {
            "huggingface": "mistralai/Mistral-Large-Instruct-2407",
            "container": "swarmos/mistral-large:v1"
        },
        "license": "apache2"
    },
}

# Infrastructure
INFRASTRUCTURE = {
    "gpus": [
        {"model": "RTX 5090", "count": 48, "vram_gb": 32, "total_vram_tb": 1.5},
        {"model": "RTX 6000 Ada", "count": 48, "vram_gb": 48, "total_vram_tb": 2.3},
        {"model": "RTX 3090", "count": 200, "vram_gb": 24, "total_vram_tb": 4.8},
    ],
    "totals": {
        "gpu_count": 296,
        "total_vram_tb": 8.6,
    },
    "power": "solar",
    "location": "Florida, USA",
}


# =============================================================================
# Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🧬 SwarmHive API starting...")
    print(f"   ENS: {config.ENS}")
    print(f"   Models: {len(MODELS)}")
    yield
    print(f"🧬 SwarmHive API shutting down...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="SwarmHive API",
    description="Model Registry for SwarmOS - Sovereign AI Models",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://swarmhive.eth.limo",
        "https://swarmorb.eth.limo",
        "https://swarmos.eth.limo",
        "http://localhost:3000",
        "http://localhost:4321",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "swarmhive",
        "version": config.VERSION,
        "models_count": len(MODELS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/models")
async def list_models(category: str = None, status: str = None):
    """List all models in the registry."""
    models = list(MODELS.values())
    
    if category:
        models = [m for m in models if m["category"] == category]
    if status:
        models = [m for m in models if m["status"] == status]
    
    return {
        "models": models,
        "total": len(models),
    }


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """Get specific model details."""
    if model_id not in MODELS:
        raise HTTPException(status_code=404, detail="Model not found")
    return MODELS[model_id]


@app.get("/v1/models/{model_id}/weights")
async def get_model_weights(model_id: str):
    """Get model weight locations."""
    if model_id not in MODELS:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model = MODELS[model_id]
    return {
        "model_id": model_id,
        "version": model["version"],
        "weights": model["weights"],
        "license": model["license"],
    }


@app.get("/v1/categories")
async def list_categories():
    """List model categories."""
    categories = {}
    for model in MODELS.values():
        cat = model["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "models": []}
        categories[cat]["count"] += 1
        categories[cat]["models"].append(model["id"])
    
    return {"categories": categories}


@app.get("/v1/categories/{category}")
async def get_category(category: str):
    """Get models in a category."""
    models = [m for m in MODELS.values() if m["category"] == category]
    if not models:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return {
        "category": category,
        "models": models,
        "total": len(models),
    }


@app.get("/v1/infrastructure")
async def get_infrastructure():
    """Get GPU infrastructure status."""
    return INFRASTRUCTURE


@app.get("/v1/benchmarks")
async def get_benchmarks():
    """Get model performance benchmarks."""
    benchmarks = []
    for model in MODELS.values():
        if model["category"] == "medical":
            benchmarks.append({
                "model_id": model["id"],
                "name": model["name"],
                "version": model["version"],
                "status": model["status"],
                "accuracy": model["performance"]["accuracy"],
                "inference_seconds": model["specs"]["inference_seconds"],
                "vram_gb": model["specs"]["vram_gb"],
            })
    
    return {
        "benchmarks": sorted(benchmarks, key=lambda x: x["accuracy"], reverse=True),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/stats")
async def get_stats():
    """Get registry statistics."""
    medical = [m for m in MODELS.values() if m["category"] == "medical"]
    llm = [m for m in MODELS.values() if m["category"] == "llm"]
    production = [m for m in MODELS.values() if m["status"] == "production"]
    
    return {
        "total_models": len(MODELS),
        "medical_models": len(medical),
        "llm_models": len(llm),
        "production_models": len(production),
        "total_gpus": INFRASTRUCTURE["totals"]["gpu_count"],
        "total_vram_tb": INFRASTRUCTURE["totals"]["total_vram_tb"],
        "avg_accuracy": sum(m["performance"]["accuracy"] for m in medical) / len(medical),
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
