#!/usr/bin/env python3
"""
Quick test script to verify the enhanced API is working correctly
"""

import requests
import json
import time

def test_enhanced_api():
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Enhanced BaseballAPI...")
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Data status
    print("\n2. Testing data status endpoint...")
    try:
        response = requests.get(f"{base_url}/data/status")
        print(f"✅ Data status: {response.status_code}")
        data = response.json()
        print(f"   Initialization status: {data.get('initialization_status')}")
        if data.get('initialization_status') != 'completed':
            print("⚠️  Data not fully initialized yet, waiting...")
            return False
    except Exception as e:
        print(f"❌ Data status failed: {e}")
        return False
    
    # Test 3: Enhanced endpoint
    print("\n3. Testing enhanced pitcher vs team endpoint...")
    try:
        payload = {
            "pitcher_name": "Test Pitcher",
            "team": "SEA",
            "include_confidence": True
        }
        response = requests.post(
            f"{base_url}/analyze/pitcher-vs-team",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )
        print(f"✅ Enhanced endpoint status: {response.status_code}")
        if response.status_code == 404:
            result = response.json()
            print(f"   Expected 404 for test pitcher: {result.get('detail', 'Unknown error')}")
        else:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Enhanced endpoint failed: {e}")
        return False
    
    # Test 4: Data quality endpoint
    print("\n4. Testing data quality endpoint...")
    try:
        response = requests.get(f"{base_url}/analyze/data-quality")
        print(f"✅ Data quality: {response.status_code}")
        data = response.json()
        print(f"   Enhanced features: {data.get('enhanced_features_active', False)}")
    except Exception as e:
        print(f"❌ Data quality failed: {e}")
        return False
    
    print("\n🎉 All enhanced API tests passed!")
    return True

def wait_for_api(max_attempts=10):
    """Wait for the API to be available"""
    print("⏳ Waiting for API to be available...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ API available after {attempt + 1} attempts")
                return True
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"   Attempt {attempt + 1}/{max_attempts} failed, retrying...")
                time.sleep(2)
            else:
                print(f"❌ API not available after {max_attempts} attempts: {e}")
                return False
    
    return False

if __name__ == "__main__":
    if wait_for_api():
        # Give it a moment to fully initialize
        time.sleep(3)
        test_enhanced_api()
    else:
        print("❌ Could not connect to API. Make sure enhanced_main.py is running on port 8000")