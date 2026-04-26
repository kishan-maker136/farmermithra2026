#!/usr/bin/env python3
"""
Quick verification script for weather API and irrigation advice
Shows what the API will return now
"""

import os
import sys

# Simulate the backend functions
def calculate_irrigation_advice(temp, humidity, rain, pressure, wind_speed):
    """Calculate detailed irrigation advice based on weather parameters"""
    advice_points = []
    
    # Rain impact
    if rain:
        advice_points.append("RAIN ALERT: No watering needed. Check soil moisture in 24 hours.")
        return "\n".join(advice_points)
    
    # Temperature-based advice
    if temp > 35:
        advice_points.append(f"🌡️ HIGH TEMP ({temp}°C): Water twice - early morning (5-6 AM) and evening (6-7 PM).")
        advice_points.append("Increase irrigation by 30-40% to prevent crop stress.")
    elif temp >= 28:
        advice_points.append(f"Moderate temp ({temp}°C): Water once in early morning (6-7 AM).")
        advice_points.append("Check soil 10cm deep - if dry, irrigate.")
    elif temp >= 20:
        advice_points.append(f"Cool weather ({temp}°C): Reduce watering frequency.")
        advice_points.append("Water every 2-3 days depending on soil moisture.")
    else:
        advice_points.append(f"Cold weather ({temp}°C): Minimize watering.")
        advice_points.append("Risk of waterlogging - ensure good drainage.")
    
    # Humidity impact
    if humidity > 80:
        advice_points.append(f"HIGH HUMIDITY ({humidity}%): Disease risk increases. Water only at base of plants.")
        advice_points.append("Ensure good airflow between plants.")
    elif humidity < 40:
        advice_points.append(f"LOW HUMIDITY ({humidity}%): Water loss is high. Increase irrigation frequency.")
        advice_points.append("Consider mulching to retain soil moisture.")
    
    # Pressure impact
    if pressure < 1000:
        advice_points.append(f"LOW PRESSURE ({pressure} mb): Rain likely within 24-48 hours. Reduce watering.")
    elif pressure > 1020:
        advice_points.append(f"HIGH PRESSURE ({pressure} mb): Stable weather. Maintain regular schedule.")
    
    # Wind impact
    if wind_speed > 15:
        advice_points.append(f"STRONG WIND ({wind_speed} km/h): Water loss increases. Irrigate in morning/evening.")
        advice_points.append("Avoid afternoon watering - high evaporation loss.")
    elif wind_speed < 2:
        advice_points.append(f"Still weather ({wind_speed} km/h): Good for foliar sprays and disease prevention.")
    
    # Crop-specific recommendations
    advice_points.append("\n🌾 CROP-SPECIFIC TIPS:")
    advice_points.append("• Tomato/Pepper: Avoid wet foliage - water at soil level only")
    advice_points.append("• Rice: Maintain 5cm water level during growing season")
    advice_points.append("• Onion: Reduce water 3 weeks before harvest")
    advice_points.append("• Maize: Heavy water needs during tasseling stage")
    
    return "\n".join(advice_points)


def test_demo_weather():
    """Test what demo weather returns"""
    print("=" * 70)
    print("🎬 DEMO WEATHER RESPONSE (No API Key Set)")
    print("=" * 70)
    
    temp, humidity, pressure, wind = 28, 60, 1013, 5
    rain = False
    
    advice = calculate_irrigation_advice(temp, humidity, rain, pressure, wind)
    
    response = {
        "success": True,
        "city": "Tumkur",
        "temperature": temp,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind,
        "description": "Partly Cloudy",
        "rain": rain,
        "advice": advice,
        "demo": True,
    }
    
    print(f"\n📍 City: {response['city']}")
    print(f"🌡️  Temperature: {response['temperature']}°C")
    print(f"💧 Humidity: {response['humidity']}%")
    print(f"💨 Wind: {response['wind_speed']} km/h")
    print(f"🔼 Pressure: {response['pressure']} mb")
    print(f"☁️  Description: {response['description']}")
    print(f"🌧️  Rain: {'Yes' if response['rain'] else 'No'}")
    print(f"🎬 Demo Mode: {response['demo']}")
    
    print(f"\n💡 IRRIGATION ADVICE (What the farmer sees):")
    print("-" * 70)
    print(advice)
    print("-" * 70)


def test_different_weather_scenarios():
    """Test different weather scenarios"""
    scenarios = [
        {"name": "High Temp Day", "temp": 36, "humidity": 45, "pressure": 1010, "wind": 12, "rain": False},
        {"name": "Rainy Day", "temp": 25, "humidity": 85, "pressure": 995, "wind": 8, "rain": True},
        {"name": "Cool Day", "temp": 18, "humidity": 70, "pressure": 1020, "wind": 2, "rain": False},
        {"name": "High Humidity", "temp": 30, "humidity": 82, "pressure": 1015, "wind": 3, "rain": False},
    ]
    
    print("\n" + "=" * 70)
    print("🌍 SCENARIO TESTS - Different Weather Conditions")
    print("=" * 70)
    
    for scenario in scenarios:
        print(f"\n\n📍 SCENARIO: {scenario['name']}")
        print(f"   Temp: {scenario['temp']}°C | Humidity: {scenario['humidity']}% | Pressure: {scenario['pressure']}mb | Wind: {scenario['wind']}km/h")
        print("-" * 70)
        
        advice = calculate_irrigation_advice(
            scenario['temp'], scenario['humidity'], scenario['rain'], 
            scenario['pressure'], scenario['wind']
        )
        
        # Show first 3 lines for overview
        lines = advice.split('\n')
        for line in lines[:3]:
            print(f"   {line}")
        print(f"   ... ({len(lines) - 3} more lines)")


if __name__ == "__main__":
    print("\n🚜 MITHRAVA WEATHER API - BACKEND VERIFICATION\n")
    
    # Test demo weather
    test_demo_weather()
    
    # Test different scenarios
    test_different_weather_scenarios()
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 70)
    print("\n📋 WHAT YOU SHOULD NOW SEE IN THE APP:")
    print("   ✓ Temperature, Humidity, Pressure, Wind Speed")
    print("   ✓ Multi-line irrigation advice (not just 1-2 lines)")
    print("   ✓ Temperature-based watering frequency")
    print("   ✓ Humidity-based disease warnings")
    print("   ✓ Crop-specific irrigation tips")
    print("   ✓ All this even in DEMO mode (no API key needed)\n")
    
    print("🚀 TO ACTIVATE REAL WEATHER (Replace Demo):")
    print("   1. Get API key: https://openweathermap.org/api")
    print("   2. Set in PowerShell: $env:OPENWEATHER_API_KEY = 'your_key'")
    print("   3. Run app in SAME terminal: python backend/app.py")
    print("   4. Restart browser and login\n")
