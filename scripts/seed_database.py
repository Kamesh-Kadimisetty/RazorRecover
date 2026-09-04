#!/usr/bin/env python3
"""
Seed Database with Demo Cases and Cohorts
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal, Base, engine
from backend.app.api.simulator_api import seed_demo_data

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Seeding database with demo cases and behavioral cohorts...")
        res = seed_demo_data(db)
        print(f"Result: {res}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
