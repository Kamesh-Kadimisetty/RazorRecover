#!/usr/bin/env python3
"""
Verify Razorpay Test Mode Credentials
Calls the official Razorpay /v1/payments endpoint to verify key validity.
"""
import os
import sys
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.config import settings

def main():
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    print("=" * 60)
    print("      VERIFYING RAZORPAY TEST MODE CREDENTIALS       ")
    print("=" * 60)
    print(f"Key ID:     {key_id[:12]}... (active)")
    print(f"Key Secret: {'*' * len(key_secret)}")

    if not key_id or not key_secret:
        print("\n❌ Error: RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET is not set in .env")
        return

    url = "https://api.razorpay.com/v1/payments?count=1"
    try:
        resp = requests.get(url, auth=(key_id, key_secret), timeout=10)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ SUCCESS: Razorpay Test Mode keys are valid and authenticated!")
            data = resp.json()
            print(f"Total payments fetched: {data.get('count', 0)}")
        else:
            print("❌ Authentication failed:")
            print(resp.text)
    except Exception as e:
        print(f"⚠️ Network error connecting to Razorpay: {e}")

    print("=" * 60)

if __name__ == "__main__":
    main()
