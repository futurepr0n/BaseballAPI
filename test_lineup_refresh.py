#!/usr/bin/env python3
"""
Test script for the updated refresh-lineups endpoint
Tests the comprehensive fetch_starting_lineups.py integration
"""

import requests
import json
import sys
from datetime import datetime

def test_lineup_refresh():
    """Test the refresh-lineups endpoint"""
    
    print("🧪 Testing Comprehensive Lineup Refresh Endpoint")
    print("=" * 60)
    
    # Test the endpoint
    try:
        print("📡 Sending POST request to /refresh-lineups...")
        response = requests.post(
            "http://localhost:8000/refresh-lineups",
            timeout=300  # 5 minute timeout for comprehensive fetch
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Request successful!")
            print(f"🎯 Message: {result.get('message', 'No message')}")
            print(f"📅 Timestamp: {result.get('timestamp', 'No timestamp')}")
            print(f"🏟️ Games Found: {result.get('games_found', 0)}")
            print(f"📋 Lineups Found: {result.get('lineups_found', 0)}")
            print(f"👥 Roster Updates: {result.get('roster_updates', 0)}")
            print(f"🐍 Script Used: {result.get('script_used', 'Unknown')}")
            
            print("\n🎯 Features Included:")
            features = result.get('features', [])
            for i, feature in enumerate(features, 1):
                print(f"   {i}. {feature}")
            
            print(f"\n📤 Script Output (first 500 chars):")
            output = result.get('output', '')
            print(f"   {output[:500]}{'...' if len(output) > 500 else ''}")
            
            # Validation checks
            print("\n🔍 Validation Results:")
            if result.get('games_found', 0) > 0:
                print("   ✅ Found games successfully")
            else:
                print("   ⚠️ No games found")
                
            if result.get('script_used') == 'fetch_starting_lineups.py':
                print("   ✅ Using comprehensive fetch_starting_lineups.py script")
            else:
                print("   ❌ Not using expected script")
                
            if 'MLB Stats API integration' in features:
                print("   ✅ MLB Stats API integration confirmed")
            else:
                print("   ❌ MLB Stats API integration not confirmed")
                
            if 'Roster enhancement' in str(features):
                print("   ✅ Roster enhancement features confirmed")
            else:
                print("   ❌ Roster enhancement features not confirmed")
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"📝 Error Details: {error_data}")
            except:
                print(f"📝 Error Text: {response.text}")
                
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - this is normal for comprehensive lineup fetching")
        print("   The script may still be running in the background")
        
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - make sure BaseballAPI is running on localhost:8000")
        print("   Start it with: python enhanced_main.py")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_lineup_service_compatibility():
    """Test that the updated endpoint returns data compatible with startingLineupService.js"""
    
    print("\n🔗 Testing Frontend Compatibility")
    print("=" * 40)
    
    try:
        # Simulate what the frontend startingLineupService.js expects
        response = requests.post("http://localhost:8000/refresh-lineups")
        
        if response.status_code == 200:
            result = response.json()
            
            # Check for required fields that startingLineupService.js expects
            required_fields = ['success', 'message']
            missing_fields = []
            
            for field in required_fields:
                if field not in result:
                    missing_fields.append(field)
                    
            if not missing_fields:
                print("✅ All required fields present for frontend compatibility")
            else:
                print(f"⚠️ Missing required fields: {missing_fields}")
                
            # Check success status
            if result.get('success') == True:
                print("✅ Success status confirmed")
            else:
                print("❌ Success status not True")
                
            print(f"📋 Frontend will see: '{result.get('message', 'No message')}'")
            
        else:
            print(f"❌ Endpoint not accessible: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Compatibility test error: {e}")

if __name__ == "__main__":
    print("🚀 BaseballAPI Lineup Refresh Test Suite")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    test_lineup_refresh()
    test_lineup_service_compatibility()
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 Next Steps:")
    print("   1. If tests pass, the PinheadsPlayhouse 'Refresh Lineups' button now uses comprehensive data")
    print("   2. The system will use fetch_starting_lineups.py instead of enhanced_lineup_scraper.py")
    print("   3. You'll get richer data including pitcher stats, handedness, and roster enhancements")