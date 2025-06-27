#!/usr/bin/env python3
"""
Test script for the enhanced opportunities endpoint
"""

import requests
import json
from datetime import datetime

def test_enhanced_opportunities_endpoint():
    """Test the enhanced opportunities endpoint with sample data"""
    
    # Test data that matches the format from HRMatchupHub
    test_request = {
        "players": [
            {
                "playerName": "Riley Greene",
                "team": "DET",
                "venue": "Comerica Park",
                "score": 87.5,
                "isHome": True,
                "gameId": "1210"
            },
            {
                "playerName": "Aaron Judge", 
                "team": "NYY",
                "venue": "Yankee Stadium",
                "score": 92.3,
                "isHome": True,
                "gameId": "1211"
            },
            {
                "playerName": "Shohei Ohtani",
                "team": "LAD", 
                "venue": "Coors Field",
                "score": 89.1,
                "isHome": False,
                "gameId": "1216"
            }
        ],
        "currentDate": "2025-06-26T00:00:00Z",
        "analysisType": "opportunities"
    }
    
    print("🚀 Testing Enhanced Opportunities Endpoint")
    print("=" * 50)
    
    try:
        # Test the endpoint
        url = "http://localhost:8000/analyze/enhanced-opportunities"
        
        print(f"📡 Making request to: {url}")
        print(f"📋 Test data: {len(test_request['players'])} players")
        
        response = requests.post(
            url,
            json=test_request,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"   - Players processed: {len(result.get('players', []))}")
            print(f"   - Total opportunities: {result.get('totalOpportunities', 0)}")
            print(f"   - Generated at: {result.get('generatedAt', 'N/A')}")
            print(f"   - Processing method: {result.get('processingTime', 'N/A')}")
            
            # Check first player's enhanced insights
            if result.get('players') and len(result['players']) > 0:
                first_player = result['players'][0]
                insights = first_player.get('enhancedInsights', {})
                
                print(f"\n🎯 Sample Player Analysis ({first_player.get('playerName', 'Unknown')}):")
                print(f"   - Has data: {insights.get('hasData', False)}")
                print(f"   - Insight score: {insights.get('insightScore', 0)}")
                print(f"   - Selection reasons: {len(insights.get('selectionReasons', []))}")
                print(f"   - Season achievements: {insights.get('seasonRankings', {}).get('hasAchievements', False)}")
                print(f"   - Active streaks: {insights.get('streakStatus', {}).get('hasActiveStreaks', False)}")
                print(f"   - Processing method: {insights.get('processingMethod', 'unknown')}")
                
                # Show selection reasons if available
                reasons = insights.get('selectionReasons', [])
                if reasons:
                    print(f"\n📝 Selection Reasons:")
                    for i, reason in enumerate(reasons[:3]):  # Show first 3
                        print(f"   {i+1}. {reason.get('icon', '')} {reason.get('text', 'No text')}")
            
            print("\n🎉 Enhanced Opportunities API is working correctly!")
            return True
            
        elif response.status_code == 503:
            print("❌ FAILED: Data not ready")
            print("   - Make sure BaseballAPI has initialized all data")
            return False
            
        elif response.status_code == 500:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"❌ FAILED: Server Error - {error_detail}")
            
            if 'Enhanced opportunities analyzer not available' in str(error_detail):
                print("   - The enhanced_opportunities_analyzer.py file may not be in the correct location")
            
            return False
            
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Cannot connect to BaseballAPI")
        print("   - Make sure BaseballAPI is running on localhost:8000")
        print("   - Run: python enhanced_main.py")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timed out")
        print("   - The server may be overloaded or processing is taking too long")
        return False
        
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False

def test_api_health():
    """Test if the BaseballAPI is running and healthy"""
    try:
        print("\n🔍 Testing API Health...")
        response = requests.get("http://localhost:8000/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print("✅ BaseballAPI is healthy")
            print(f"   - Status: {health_data.get('status', 'unknown')}")
            print(f"   - Data initialized: {health_data.get('data_initialized', False)}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Enhanced Opportunities API Test")
    print("=" * 50)
    
    # Test API health first
    if test_api_health():
        # Run the main test
        test_enhanced_opportunities_endpoint()
    else:
        print("\n⚠️ Skipping enhanced opportunities test due to API health issues")
        print("\nTo fix:")
        print("1. Navigate to BaseballAPI directory")
        print("2. Run: python enhanced_main.py")
        print("3. Wait for data initialization to complete")
        print("4. Run this test again")