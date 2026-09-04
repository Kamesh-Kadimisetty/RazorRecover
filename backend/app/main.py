import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.schemas import RecoveryCase
from backend.app.api import webhooks, cases, metrics, simulator_api, evaluation_api, policies_api
from backend.app.api.simulator_api import seed_demo_data

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Revenue Recovery Agent for Razorpay Buildathon (Track 03)"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(webhooks.router)
app.include_router(cases.router)
app.include_router(metrics.router)
app.include_router(simulator_api.router)
app.include_router(evaluation_api.router)
app.include_router(policies_api.router)

# Automatic initial seed if DB is empty
@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        if db.query(RecoveryCase).count() == 0:
            seed_demo_data(db)
    finally:
        db.close()

# Mount Static Files for Merchant Dashboard UI
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mode": settings.MODE,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
