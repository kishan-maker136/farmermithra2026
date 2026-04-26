from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import base64
import datetime as dt
import io
import json
import os
import random
from threading import Lock

import requests

try:
    import numpy as np
    from PIL import Image
    import tensorflow as tf
    ML_AVAILABLE = True
except ImportError:
    np = None
    Image = None
    tf = None
    ML_AVAILABLE = False


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

FARMERS_FILE = os.path.join(BASE_DIR, "farmers_db")
VENDORS_FILE = os.path.join(BASE_DIR, "vendors_db")
CALLS_FILE = os.path.join(BASE_DIR, "call_requests.json")
MODEL_FILE = os.path.join(BASE_DIR, "model.h5")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "demo")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

FARMING_SYSTEM_PROMPT = """You are Mithrava AI, an expert farming assistant for Indian farmers.
You help with:
- Crop advice (when to sow, harvest, water)
- Irrigation guidance
- Pesticide and fertilizer recommendations
- Disease identification
- Weather-based farming decisions
- Market price tips

You support English, Hindi, Kannada, Telugu, and regional slang.
Always respond in the same language the farmer is using.
Keep answers short, clear, and practical for farmers.
If asked in Hindi slang or regional dialects, understand and respond accordingly."""

DISEASE_LABELS = [
    "Apple Scab",
    "Apple Black Rot",
    "Cedar Apple Rust",
    "Healthy Apple",
    "Tomato Early Blight",
    "Tomato Late Blight",
    "Tomato Healthy",
    "Corn Common Rust",
    "Corn Healthy",
    "Potato Early Blight",
    "Potato Healthy",
]

DISEASE_TREATMENTS = {
    "Apple Scab": "Apply Captan or Myclobutanil fungicide. Remove infected leaves.",
    "Apple Black Rot": "Prune infected branches. Apply copper-based fungicide.",
    "Cedar Apple Rust": "Use Myclobutanil spray. Remove nearby cedar trees if possible.",
    "Healthy Apple": "Plant looks healthy. Continue regular care.",
    "Tomato Early Blight": "Apply Mancozeb 2.5g/liter. Ensure good airflow between plants.",
    "Tomato Late Blight": "Use Metalaxyl spray immediately. Remove infected plants.",
    "Tomato Healthy": "Plant is healthy. Maintain regular watering schedule.",
    "Corn Common Rust": "Apply Propiconazole fungicide. Remove heavily infected leaves.",
    "Corn Healthy": "Corn looks healthy. Check for pests weekly.",
    "Potato Early Blight": "Apply Chlorothalonil 2g/liter. Water at base, avoid leaves.",
    "Potato Healthy": "Plant is healthy. Monitor for late blight in humid weather.",
}

DEMO_FARMERS = {
    "9876543210": {
        "name": "Raju Patil",
        "phone": "9876543210",
        "city": "Pune",
        "lands": [
            {
                "crop": "Tomato",
                "crop_name": "Tomato",
                "area": "2.5",
                "area_acres": "2.5",
                "sowing_date": "2026-03-15",
                "status": "active",
            },
            {
                "crop": "Onion",
                "crop_name": "Onion",
                "area": "1.8",
                "area_acres": "1.8",
                "sowing_date": "2026-02-10",
                "status": "harvest",
            },
        ],
    }
}

DEMO_VENDORS = [
    {"id": 1, "shop_name": "Krishi Bhandar", "city": "pune", "type": "Seeds"},
    {"id": 2, "shop_name": "Agro Supplies Plus", "city": "pune", "type": "Fertilizer"},
    {"id": 3, "shop_name": "Green Farm Store", "city": "pune", "type": "Pesticide"},
]

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

store_lock = Lock()
otp_store = {}


def ensure_storage_file(path, default_data):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(default_data, file, indent=2)
        return

    if os.path.isdir(path):
        raise RuntimeError(f"Storage path is a directory: {path}")

    if os.path.getsize(path) == 0:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(default_data, file, indent=2)


def load_json_file(path, default_data):
    ensure_storage_file(path, default_data)
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(default_data, file, indent=2)
        return default_data


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def normalize_land(land):
    crop_name = str(land.get("crop_name") or land.get("crop") or "").strip()
    area_value = land.get("area_acres")
    if area_value in (None, ""):
        area_value = land.get("area", "")
    area_text = str(area_value).strip() if area_value is not None else ""
    sowing_date = str(land.get("sowing_date") or "N/A").strip() or "N/A"
    status = str(land.get("status") or "active").strip().lower()
    if status not in {"active", "harvest"}:
        status = "active"

    return {
        "crop": crop_name,
        "crop_name": crop_name,
        "area": area_text,
        "area_acres": area_text,
        "sowing_date": sowing_date,
        "status": status,
    }


def normalize_farmer(farmer):
    phone = str(farmer.get("phone") or "").strip()
    lands = farmer.get("lands") or []
    normalized_lands = [normalize_land(land) for land in lands if normalize_land(land)["crop_name"]]

    return {
        "name": str(farmer.get("name") or "").strip(),
        "phone": phone,
        "city": str(farmer.get("city") or "").strip(),
        "lands": normalized_lands,
    }


def normalize_vendor(vendor, vendor_id):
    return {
        "id": vendor_id,
        "shop_name": str(vendor.get("shop_name") or "").strip(),
        "city": str(vendor.get("city") or "").strip().lower(),
        "type": str(vendor.get("type") or "General").strip() or "General",
    }


def normalize_call(call, call_id):
    timestamp = call.get("timestamp") or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = str(call.get("status") or "pending").strip().lower() or "pending"
    return {
        "id": call_id,
        "phone": str(call.get("phone") or "").strip(),
        "name": str(call.get("name") or "").strip(),
        "city": str(call.get("city") or "").strip(),
        "message": str(call.get("message") or "").strip(),
        "timestamp": timestamp,
        "status": status,
    }


def load_state():
    raw_farmers = load_json_file(FARMERS_FILE, DEMO_FARMERS)
    raw_vendors = load_json_file(VENDORS_FILE, DEMO_VENDORS)
    raw_calls = load_json_file(CALLS_FILE, [])

    if isinstance(raw_farmers, list):
        farmers = {}
        for farmer in raw_farmers:
            normalized = normalize_farmer(farmer)
            if normalized["phone"]:
                farmers[normalized["phone"]] = normalized
    else:
        farmers = {}
        for phone, farmer in raw_farmers.items():
            normalized = normalize_farmer({**farmer, "phone": farmer.get("phone") or phone})
            if normalized["phone"]:
                farmers[normalized["phone"]] = normalized

    vendors = [normalize_vendor(vendor, index + 1) for index, vendor in enumerate(raw_vendors or [])]
    calls = [normalize_call(call, index + 1) for index, call in enumerate(raw_calls or [])]

    return farmers, vendors, calls


def persist_farmers():
    save_json_file(FARMERS_FILE, farmers_db)


def persist_vendors():
    save_json_file(VENDORS_FILE, vendors_db)


def persist_calls():
    save_json_file(CALLS_FILE, call_requests)


farmers_db, vendors_db, call_requests = load_state()


def next_vendor_id():
    return max((vendor["id"] for vendor in vendors_db), default=0) + 1


def next_call_id():
    return max((call["id"] for call in call_requests), default=0) + 1


def get_request_json():
    return request.get_json(silent=True) or {}


def weather_demo(city):
    return {
        "success": True,
        "city": city,
        "temperature": 28,
        "humidity": 60,
        "description": "Partly Cloudy",
        "rain": False,
        "pressure": 1013,
        "wind_speed": 5,
        "advice": "Water your crops today. No rain expected.",
        "irrigation_advice": "Demo data - irrigate 1-2 times daily depending on crop type.",
        "demo": True,
    }


def calculate_irrigation_advice(temp, humidity, rain, pressure, wind_speed):
    """Calculate detailed irrigation advice based on weather parameters"""
    advice_points = []
    
    # Rain impact
    if rain:
        advice_points.append("RAIN ALERT: No watering needed. Check soil moisture in 24 hours.")
        return " ".join(advice_points)
    
    # Calculate evapotranspiration index (simplified)
    # High temp + low humidity + wind = high water loss
    evapotranspiration = (temp / 30) * (1 - humidity / 100) * (1 + wind_speed / 10)
    
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


def answer_from_demo(question):
    demo_answers = {
        "water": "Water your crops early morning between 6 AM and 8 AM. Avoid watering at noon.",
        "disease": "Check leaves for yellowing or dark spots. Start with a neem-based spray and remove badly affected leaves.",
        "fertilizer": "Use a balanced fertilizer during growth. Apply only as needed and water after application.",
        "pest": "Spray in the evening and inspect the underside of leaves. Start with the mildest effective option.",
        "weather": "Check local weather before watering. If rain is likely, reduce irrigation to save water.",
    }

    q_lower = question.lower()
    for key, value in demo_answers.items():
        if key in q_lower:
            return value

    return "I can help with crop care, irrigation, plant disease, pests, and fertilizers. Ask a more specific farming question."


def load_disease_model():
    if not ML_AVAILABLE or not os.path.exists(MODEL_FILE):
        return None

    try:
        model = tf.keras.models.load_model(MODEL_FILE)
        print("[INFO] Disease model loaded.")
        return model
    except Exception as exc:
        print(f"[WARN] Could not load model.h5: {exc}")
        return None


disease_model = load_disease_model()


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.route("/index.html", methods=["GET"])
def index_page():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.route("/login.html", methods=["GET"])
def login_page():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.route("/dashboard.html", methods=["GET"])
def dashboard_page():
    return send_from_directory(FRONTEND_DIR, "dashboard.html")


@app.route("/adminpanel.html", methods=["GET"])
def adminpanel_page():
    return send_from_directory(FRONTEND_DIR, "adminpanel.html")


@app.route("/admin.html", methods=["GET"])
def admin_page():
    return send_from_directory(FRONTEND_DIR, "adminpanel.html")


@app.route("/style.css", methods=["GET"])
def style_page():
    return send_from_directory(FRONTEND_DIR, "style.css")


@app.route("/ask", methods=["POST"])
def ask():
    return ask_ai()


@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = get_request_json()
    phone = str(data.get("phone") or "").strip()

    if not phone or len(phone) < 10:
        return jsonify({"success": False, "message": "Invalid phone number"}), 400

    otp = str(random.randint(100000, 999999))
    otp_store[phone] = otp
    farmer = farmers_db.get(phone)
    role = "farmer" if farmer else "unknown"

    print(f"[OTP] Phone: {phone} OTP: {otp}")
    return jsonify({
        "success": True,
        "otp": otp,
        "role": role,
        "message": "OTP generated (displayed for MVP)",
    })


@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = get_request_json()
    phone = str(data.get("phone") or "").strip()
    otp = str(data.get("otp") or "").strip()

    if otp_store.get(phone) != otp:
        return jsonify({"success": False, "message": "Invalid OTP"}), 401

    farmer = farmers_db.get(phone)
    if not farmer:
        return jsonify({
            "success": False,
            "message": "Farmer not registered. Contact admin.",
            "role": "not_found",
        }), 404

    return jsonify({"success": True, "farmer": farmer, "message": "Login successful"})


@app.route("/add_farmer", methods=["POST"])
def add_farmer():
    data = get_request_json()
    phone = str(data.get("phone") or "").strip()

    if not phone:
        return jsonify({"success": False, "message": "Phone is required"}), 400

    farmer = normalize_farmer(data)
    if not farmer["name"] or not farmer["city"]:
        return jsonify({"success": False, "message": "Name, phone, and city are required"}), 400

    if not farmer["lands"]:
        return jsonify({"success": False, "message": "At least one crop is required"}), 400

    with store_lock:
        farmers_db[phone] = farmer
        persist_farmers()

    return jsonify({"success": True, "message": "Farmer added", "farmer": farmer})


@app.route("/add_vendor", methods=["POST"])
def add_vendor():
    data = get_request_json()
    shop_name = str(data.get("shop_name") or "").strip()
    city = str(data.get("city") or "").strip()

    if not shop_name or not city:
        return jsonify({"success": False, "message": "Shop name and city are required"}), 400

    with store_lock:
        vendor = normalize_vendor(data, next_vendor_id())
        vendors_db.append(vendor)
        persist_vendors()

    return jsonify({"success": True, "message": "Vendor added", "vendor": vendor})


@app.route("/get_vendors/<city>", methods=["GET"])
def get_vendors(city):
    city_clean = city.strip().lower()
    if city_clean == "all":
        return jsonify({"success": True, "vendors": vendors_db})

    matches = [vendor for vendor in vendors_db if vendor["city"] == city_clean]
    return jsonify({"success": True, "vendors": matches})


@app.route("/get_calls", methods=["GET"])
def get_calls():
    return jsonify({"success": True, "calls": call_requests})


@app.route("/get_farmers", methods=["GET"])
def get_farmers():
    return jsonify({"success": True, "farmers": list(farmers_db.values())})


@app.route("/request_call", methods=["POST"])
def request_call():
    data = get_request_json()

    phone = str(data.get("phone") or "").strip()
    if not phone:
        return jsonify({"success": False, "message": "Phone number is required"}), 400

    with store_lock:
        call = normalize_call(
            {
                "phone": phone,
                "name": data.get("name"),
                "city": data.get("city"),
                "message": data.get("message"),
                "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pending",
            },
            next_call_id(),
        )
        call_requests.append(call)
        persist_calls()

    return jsonify({"success": True, "message": "Call request submitted", "call": call})


@app.route("/get_weather/<city>", methods=["GET"])
def get_weather_endpoint(city):
    city_name = city.strip()
    
    # If no valid API key, return demo data with calculated advice
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "demo":
        # Demo weather values that represent typical Indian summer conditions
        demo_temp = 28
        demo_humidity = 60
        demo_pressure = 1013
        demo_wind = 5
        demo_rain = False
        
        # Calculate advice even for demo data
        irrigation_advice = calculate_irrigation_advice(
            demo_temp, demo_humidity, demo_rain, demo_pressure, demo_wind
        )
        
        return jsonify({
            "success": True,
            "city": city_name,
            "temperature": demo_temp,
            "humidity": demo_humidity,
            "pressure": demo_pressure,
            "wind_speed": demo_wind,
            "description": "Partly Cloudy",
            "rain": demo_rain,
            "advice": irrigation_advice,
            "demo": True,
        })

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        response = requests.get(
            url,
            params={"q": city_name, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
        response.raise_for_status()
        weather = response.json()

        # Extract all relevant weather data
        temp = float(weather["main"]["temp"])
        humidity = int(weather["main"]["humidity"])
        pressure = int(weather["main"].get("pressure", 1013))
        wind_speed = float(weather["wind"].get("speed", 0))
        description = str(weather["weather"][0]["description"])
        rain = "rain" in description.lower() or weather.get("rain") is not None
        
        # Calculate irrigation advice based on all factors
        irrigation_advice = calculate_irrigation_advice(temp, humidity, rain, pressure, wind_speed)

        return jsonify({
            "success": True,
            "city": city_name,
            "temperature": round(temp, 1),
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": round(wind_speed, 1),
            "description": description.title(),
            "rain": rain,
            "advice": irrigation_advice,
            "feels_like": round(float(weather["main"].get("feels_like", temp)), 1),
            "conditions": {
                "temp_min": round(float(weather["main"]["temp_min"]), 1),
                "temp_max": round(float(weather["main"]["temp_max"]), 1),
                "visibility": weather.get("visibility", "N/A"),
                "cloudiness": weather["clouds"].get("all", 0),
            },
            "last_updated": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except requests.exceptions.RequestException as exc:
        print(f"[ERROR] Weather API Error: {exc}")
        # Return demo data with calculated advice on API failure
        demo_temp = 28
        demo_humidity = 60
        demo_pressure = 1013
        demo_wind = 5
        demo_rain = False
        irrigation_advice = calculate_irrigation_advice(
            demo_temp, demo_humidity, demo_rain, demo_pressure, demo_wind
        )
        return jsonify({
            "success": True,
            "city": city_name,
            "temperature": demo_temp,
            "humidity": demo_humidity,
            "pressure": demo_pressure,
            "wind_speed": demo_wind,
            "description": "Partly Cloudy",
            "rain": demo_rain,
            "advice": irrigation_advice,
            "demo": True,
            "message": f"Real API failed, showing demo data.",
        }), 200
    except Exception as exc:
        print(f"[ERROR] Unexpected error: {exc}")
        # Return demo data with calculated advice on error
        demo_temp = 28
        demo_humidity = 60
        demo_pressure = 1013
        demo_wind = 5
        demo_rain = False
        irrigation_advice = calculate_irrigation_advice(
            demo_temp, demo_humidity, demo_rain, demo_pressure, demo_wind
        )
        return jsonify({
            "success": True,
            "city": city_name,
            "temperature": demo_temp,
            "humidity": demo_humidity,
            "pressure": demo_pressure,
            "wind_speed": demo_wind,
            "description": "Partly Cloudy",
            "rain": demo_rain,
            "advice": irrigation_advice,
            "demo": True,
            "message": f"Error processing weather data.",
        }), 200


@app.route("/ask_ai", methods=["POST"])
def ask_ai():
    data = get_request_json()
    question = str(data.get("question") or "").strip()
    language = str(data.get("language") or "English").strip()
    context = str(data.get("context") or "").strip()

    if not question:
        return jsonify({"success": False, "message": "Question is required"}), 400

    prompt = (
        f"{FARMING_SYSTEM_PROMPT}\n\n"
        f"Farmer context: {context or 'Not provided'}\n"
        f"Language: {language}\n\n"
        f"Farmer asks: {question}"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        answer = str(result.get("response") or "").strip() or answer_from_demo(question)
        return jsonify({"success": True, "answer": answer})
    except requests.exceptions.RequestException:
        return jsonify({
            "success": True,
            "answer": answer_from_demo(question),
            "demo": True,
            "note": "Ollama not running. Using demo response.",
        })
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/predict_disease", methods=["POST"])
def predict_disease():
    json_body = get_request_json()

    if "image" not in request.files and "image_data" not in json_body:
        return jsonify({"success": False, "message": "No image provided"}), 400

    try:
        if "image" in request.files:
            image_bytes = request.files["image"].read()
        else:
            image_data = str(json_body["image_data"])
            image_bytes = base64.b64decode(image_data.split(",")[-1])

        if disease_model is not None and ML_AVAILABLE and Image is not None and np is not None:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
            array = np.array(image, dtype="float32") / 255.0
            array = np.expand_dims(array, axis=0)
            prediction = disease_model.predict(array, verbose=0)
            index = int(np.argmax(prediction))
            confidence = float(np.max(prediction))
            disease = DISEASE_LABELS[index] if index < len(DISEASE_LABELS) else "Unknown"
            demo_mode = False
        else:
            disease = random.choice(DISEASE_LABELS)
            confidence = round(random.uniform(0.75, 0.97), 2)
            demo_mode = True

        treatment = DISEASE_TREATMENTS.get(disease, "Consult a local agriculture officer.")
        return jsonify({
            "success": True,
            "disease": disease,
            "confidence": round(confidence * 100, 1),
            "treatment": treatment,
            "demo": demo_mode,
        })
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "ml_loaded": bool(disease_model),
        "farmers": len(farmers_db),
        "vendors": len(vendors_db),
        "calls": len(call_requests),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)