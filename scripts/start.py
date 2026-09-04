#!/usr/bin/env python3
"""
RazorRecover Launcher Script
Starts the FastAPI Backend and Merchant Dashboard on http://localhost:8000
"""
import os
import sys
import uvicorn

# Set project root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import engine, Base, SessionLocal
from backend.app.models.schemas import RecoveryCase
from backend.app.api.simulator_api import seed_demo_data
from backend.app.config import settings

def main():
    print("=" * 70)
    print("         RAZORRECOVER — AUTONOMOUS REVENUE RECOVERY AGENT         ")
    print("                Razorpay AI Buildathon (Track 03)                ")
    print("=" * 70)
    print(f"Mode: {settings.MODE.upper()}")
    print("Initializing SQLite Database...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        case_count = db.query(RecoveryCase).count()
        if case_count == 0:
            print("Seeding initial demo cases & behavioral cohorts...")
            seed_demo_data(db)
            print(f"Seeded {db.query(RecoveryCase).count()} cases.")
        else:
            print(f"Database contains {case_count} existing recovery cases.")
    finally:
        db.close()

    print("\nStarting Web Application...")
    print("Merchant Command Center: http://localhost:8000")
    print("Interactive API Docs:    http://localhost:8000/docs")
    print("=" * 70 + "\n")

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
