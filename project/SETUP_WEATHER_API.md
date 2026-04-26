# Weather API Configuration Guide

## How to Use Your OpenWeather API Key

Your app is now enhanced with **real weather data** and **comprehensive irrigation advice**. Follow these steps to activate it:

### Step 1: Get Your API Key
1. Go to [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up (free tier available)
3. Get your API key from the dashboard
4. API key format: `9ed0c193ce422071d13a37b5cd8b8dc8` (example)

### Step 2: Set Environment Variable

#### Option A: Windows PowerShell (Recommended for Development)
```powershell
# Set environment variable temporarily in current session
$env:OPENWEATHER_API_KEY = "your_api_key_here"

# Then run your Flask app
python backend/app.py
```

#### Option B: Windows Environment Variables (Permanent)
1. Press `Win + X` → Select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Click "New" under User variables
5. Variable name: `OPENWEATHER_API_KEY`
6. Variable value: `your_api_key_here`
7. Click OK and restart your terminal/IDE

#### Option C: Create .env file (Recommended for Production)
Create `backend/.env` file:
```
OPENWEATHER_API_KEY=your_api_key_here
```

Then modify `backend/app.py` to load it (add near the top after imports):
```python
from dotenv import load_dotenv
load_dotenv()
```

Install python-dotenv:
```bash
pip install python-dotenv
```

### Step 3: Test Your Setup
```powershell
# In PowerShell
$env:OPENWEATHER_API_KEY = "your_api_key_here"
python backend/app.py

# Test the endpoint
# Visit: http://localhost:5000/get_weather/Pune
```

## What You Get Now

### Real Weather Data
- ✅ Current temperature, humidity, pressure
- ✅ Wind speed and cloud coverage  
- ✅ Weather description & rain detection
- ✅ "Feels like" temperature

### Enhanced Irrigation Advice Includes
- 🌡️ **Temperature-based irrigation** (how many times to water)
- 💧 **Humidity considerations** (disease risk management)
- 💨 **Wind impact** (evaporation rates)
- 🌧️ **Pressure trends** (rain predictions)
- 🌾 **Crop-specific tips** (Tomato, Rice, Onion, Maize, etc.)

## Example Response

```json
{
  "success": true,
  "city": "Pune",
  "temperature": 32.5,
  "humidity": 55,
  "pressure": 1010,
  "wind_speed": 8.2,
  "description": "Scattered Clouds",
  "rain": false,
  "feels_like": 31.8,
  "advice": "🌡️ HIGH TEMP (32.5°C): Water twice - early morning (5-6 AM) and evening (6-7 PM)...",
  "conditions": {
    "temp_min": 28.5,
    "temp_max": 35.2,
    "visibility": 10000,
    "cloudiness": 40
  }
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Weather API error" | Check API key is correct and has spaces removed |
| Demo data returned | API key not set in environment variable |
| Timeout error | Check internet connection & OpenWeatherMap status |
| Invalid city | Use correct city name (case-insensitive) |

## API Limits (Free Tier)
- **Calls per minute**: 60
- **Calls per day**: 1,000,000
- Sufficient for real-time farming app

---
Your app now provides **intelligent, weather-based irrigation guidance** for farmers! 🚜
