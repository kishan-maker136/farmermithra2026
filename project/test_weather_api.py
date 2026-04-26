#!/usr/bin/env python3
"""
Test script to verify weather API and irrigation advice is working
Run this after setting your API key in environment
"""

import os
import requests
import sys

# Test configuration
TEST_CITIES = ["Pune", "Bangalore", "Delhi"]
API_URL = "http://localhost:5000"

def test_weather_api():
    """Test the weather endpoint"""
    print("=" * 60)
    print("🌤️  WEATHER API TEST")
    print("=" * 60)
    
    api_key = os.getenv("OPENWEATHER_API_KEY", "NOT_SET")
    print(f"\n📍 API Key Status: {api_key if api_key != 'NOT_SET' else '❌ NOT SET'}")
    
    if api_key == "NOT_SET":
        print("\n⚠️  WARNING: API key not found in environment!")
        print("To use real weather data, set: $env:OPENWEATHER_API_KEY = 'your_key_here'")
        print("Currently running in DEMO MODE\n")
    
    for city in TEST_CITIES:
        print(f"\n📍 Testing: {city}")
        print("-" * 60)
        
        try:
            response = requests.get(f"{API_URL}/get_weather/{city}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: SUCCESS")
                print(f"   Temp: {data.get('temperature')}°C")
                print(f"   Humidity: {data.get('humidity')}%")
                print(f"   Description: {data.get('description')}")
                print(f"   Pressure: {data.get('pressure')} mb")
                print(f"   Wind: {data.get('wind_speed')} km/h")
                
                if data.get('demo'):
                    print(f"   🎬 Mode: DEMO (No real API)")
                else:
                    print(f"   🔴 Mode: REAL DATA ✨")
                
                advice = data.get('advice', '')
                print(f"\n   🌾 IRRIGATION ADVICE:")
                for line in advice.split('\n')[:3]:  # Show first 3 lines
                    print(f"   {line}")
                if len(advice.split('\n')) > 3:
                    print(f"   ... and more crop tips")
            else:
                print(f"❌ Error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection Error: Is Flask running on port 5000?")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    return True

def test_demo_data():
    """Show what demo data looks like"""
    print("\n" + "=" * 60)
    print("📊 DEMO DATA SAMPLE")
    print("=" * 60)
    
    demo_response = {
        "city": "Pune",
        "temperature": 28,
        "humidity": 60,
        "pressure": 1013,
        "wind_speed": 5,
        "description": "Partly Cloudy",
        "irrigation_advice": "Demo mode - replace with real API key"
    }
    
    for key, value in demo_response.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    print("\n🚜 MITHRAVA WEATHER API TEST SUITE\n")
    
    # Try to connect to Flask
    print("Checking Flask connection...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ Flask is running!\n")
            test_weather_api()
        else:
            print(f"❌ Flask returned: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask on http://localhost:5000")
        print("\n   Make sure to run: python backend/app.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    test_demo_data()
    
    print("\n" + "=" * 60)
    print("✨ Test complete! Check output above for results.")
    print("=" * 60 + "\n")
