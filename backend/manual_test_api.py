#!/usr/bin/env python
"""
Quick test script to verify the API is working.
Run this after starting the server with: python test_api.py
"""
import asyncio
import httpx
import json


async def test_api():
    """Test basic API endpoints."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        assert response.status_code == 200

        # Test root endpoint
        print("\nTesting root endpoint...")
        response = await client.get(f"{base_url}/")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        assert response.status_code == 200

        # Test docs endpoint (if in debug mode)
        print("\nTesting docs endpoint...")
        response = await client.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("  ✓ API documentation available")
        else:
            print("  ✗ API documentation not available (debug mode off)")

        print("\n✅ All basic tests passed!")


if __name__ == "__main__":
    asyncio.run(test_api())