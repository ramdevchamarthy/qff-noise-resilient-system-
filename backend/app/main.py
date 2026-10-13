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
app.include_router(router)


from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

DIST_DIR = ROOT_DIR / "frontend" / "dist"
if (DIST_DIR / "index.html").exists():
    if (DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(str(DIST_DIR / "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path in ["docs", "openapi.json", "redoc"]:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(DIST_DIR / "index.html"))
else:
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
