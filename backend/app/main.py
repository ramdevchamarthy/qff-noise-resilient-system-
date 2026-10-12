"""
FastAPI Server Entrypoint for Noise-Resilient Quantum System.
Qiskit Fall Fest 2026 | PS-Q3: Noise-Resilient Variational Classifier
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes import router

app = FastAPI(
    title="Noise-Resilient Quantum System API",
    description="Backend API for Qiskit Fall Fest 2026 PS-Q3 (Noise-Resilient Variational Classifier)",
    version="1.0.0",
)

# CORS Configuration for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "project": "Noise-Resilient System Prototype",
        "hackathon": "Qiskit Fall Fest 2026",
        "track": "Quantum Machine Learning (Variational QML)",
        "problem_statement": "PS-Q3: Noise-Resilient Variational Classifier",
        "docs_url": "/docs",
        "api_health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
