import os
import sqlite3
import markdown
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

import base64
import io
import speech_recognition as sr
from pydub import AudioSegment

from openai import AzureOpenAI
import tensorflow as tf
import pickle
from PIL import Image
import numpy as np
import traceback
from werkzeug.utils import secure_filename

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "{API KEY HERE}")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-openai-endpoint.openai.azure.com")

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-10-21",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# Optionally, define your deployment endpoints
endpoints = {
    "gpt_40": "gpt-4o-2",
    "gpt_o1_mini": "o1-mini"
}

from flask import Flask, render_template, request, jsonify, url_for, redirect, session, flash
import requests
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_default_secret_key")  # Set a secure secret key!

def convert_markdown(md_text):
    return markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'nl2br'])

# ------------------------------
# Weather and Coordinate Functions
# ------------------------------
def compute_center(coordinates):
    lats = [coord["lat"] for coord in coordinates]
    lons = [coord["lon"] for coord in coordinates]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2
    return center_lat, center_lon

def get_weather(latitude, longitude, forecast_type="hourly"):
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto"
    }
    if forecast_type == "hourly":
        params["current_weather"] = "true"
        params["hourly"] = (
            "temperature_2m,relative_humidity_2m,dew_point_2m,"
            "precipitation,precipitation_probability,rain,showers,snowfall,weathercode,"
            "soil_temperature_0cm,soil_moisture_0_to_1cm,wind_speed_10m,wind_gusts_10m"
        )
    elif forecast_type == "daily":
        params["daily"] = (
            "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,uv_index_max"
        )
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    return response.json()

def map_weather_icon(weathercode):
    if weathercode == 0:
        return "sun.png"
    elif weathercode in [1, 2, 3]:
        return "partly_cloudy.png"
    elif weathercode in [45, 48]:
        return "fog.png"
    elif weathercode in [51, 53, 55]:
        return "drizzle.png"
    elif weathercode in [61, 63, 65]:
        return "rain.png"
    elif weathercode in [71, 73, 75]:
        return "snow.png"
    elif weathercode in [95, 96, 99]:
        return "thunderstorm.png"
    else:
        return "default.png"

# ------------------------------
# Database Helper Functions
# ------------------------------
def get_db_connection():
    conn = sqlite3.connect("farms.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_user_farms(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    farms = cursor.execute("SELECT * FROM farms WHERE user_id=?", (user_id,)).fetchall()
    farms_with_equipment = []
    for farm in farms:
        equipments = cursor.execute("SELECT * FROM equipment WHERE farm_id=?", (farm["id"],)).fetchall()
        farm_dict = dict(farm)
        farm_dict["equipments"] = [dict(eq) for eq in equipments]
        farms_with_equipment.append(farm_dict)
    conn.close()
    return farms_with_equipment

# ------------------------------
# Login and Logout functionality
# ------------------------------
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == "admin" and password == "password":
            session["username"] = username
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials. Please try again.")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

def login_required(func):
    from functools import wraps
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return decorated_view

@app.route("/home")
@login_required
def home():
    user_id = 1  # For demo purposes; in production, fetch from session
    farms = get_user_farms(user_id)
    now = datetime.now()
    return render_template("home.html", now=now, username=session.get("username"), farms=farms)

@app.route("/add_farm", methods=["GET", "POST"])
@login_required
def add_farm():
    user_id = 1
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        name = request.form.get("name")
        state = request.form.get("state")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        description = request.form.get("description")
        
        cursor.execute(
            "INSERT INTO farms (user_id, name, state, latitude, longitude, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, state, latitude, longitude, description)
        )
        conn.commit()
        conn.close()
        flash("Farm added successfully!")
        return redirect(url_for("home"))
    return render_template("add_farm.html", username=session.get("username"), now=datetime.now())

@app.route("/update_farm/<int:farm_id>", methods=["GET", "POST"])
@login_required
def update_farm(farm_id):
    user_id = 1
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        name = request.form.get("name")
        state = request.form.get("state")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        description = request.form.get("description")
        cursor.execute(
            "UPDATE farms SET name=?, state=?, latitude=?, longitude=?, description=? WHERE id=? AND user_id=?",
            (name, state, latitude, longitude, description, farm_id, user_id)
        )
        
        equipment_ids = request.form.getlist("equipment_ids")
        for eq_id in equipment_ids:
            eq_name = request.form.get(f"equipment_{eq_id}_name")
            eq_type = request.form.get(f"equipment_{eq_id}_type")
            eq_working_speed = request.form.get(f"equipment_{eq_id}_working_speed")
            eq_soil_type = request.form.get(f"equipment_{eq_id}_soil_type")
            eq_width = request.form.get(f"equipment_{eq_id}_width")
            eq_operating_cost = request.form.get(f"equipment_{eq_id}_operating_cost")
            eq_details = request.form.get(f"equipment_{eq_id}_details")
            cursor.execute(
                "UPDATE equipment SET name=?, type=?, working_speed=?, soil_type=?, width=?, operating_cost=?, details=? WHERE id=?",
                (eq_name, eq_type, eq_working_speed, eq_soil_type, eq_width, eq_operating_cost, eq_details, eq_id)
            )
        
        new_names = request.form.getlist("new_equipment_name[]")
        new_types = request.form.getlist("new_equipment_type[]")
        new_working_speeds = request.form.getlist("new_equipment_working_speed[]")
        new_soil_types = request.form.getlist("new_equipment_soil_type[]")
        new_widths = request.form.getlist("new_equipment_width[]")
        new_operating_costs = request.form.getlist("new_equipment_operating_cost[]")
        new_details_list = request.form.getlist("new_equipment_details[]")
        
        for name, type_, ws, soil, width, op_cost, details in zip(
            new_names, new_types, new_working_speeds, new_soil_types, new_widths, new_operating_costs, new_details_list
        ):
            if name.strip():
                cursor.execute(
                    "INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (farm_id, name, type_, ws, soil, width, op_cost, details)
                )
                
        conn.commit()
        conn.close()
        flash("Farm and equipment updated successfully.")
        return redirect(url_for("home"))
    else:
        farm = cursor.execute("SELECT * FROM farms WHERE id=? AND user_id=?", (farm_id, user_id)).fetchone()
        equipments = cursor.execute("SELECT * FROM equipment WHERE farm_id=?", (farm_id,)).fetchall()
        conn.close()
        if not farm:
            flash("Farm not found or unauthorized.")
            return redirect(url_for("home"))
        farm_dict = dict(farm)
        farm_dict["equipments"] = [dict(eq) for eq in equipments]
        return render_template("update_farm.html", farm=farm_dict, username=session.get("username"), now=datetime.now())

@app.route("/delete_farm/<int:farm_id>")
@login_required
def delete_farm(farm_id):
    user_id = 1
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipment WHERE farm_id=?", (farm_id,))
    cursor.execute("DELETE FROM farms WHERE id=? AND user_id=?", (farm_id, user_id))
    conn.commit()
    conn.close()
    flash("Farm deleted successfully.")
    return redirect(url_for("home"))

# ------------------------------
# Weather Dashboard and Chatbot Routes
# ------------------------------
@app.route("/weather", methods=["GET", "POST"])
@login_required
def dashboard():
    farm_name = None
    forecast_data = None
    center_coords = None
    forecast_type = None
    error = None

    illinois_coords = [
        {"lat": 40.8663889, "lon": -88.6705556},
        {"lat": 40.8663889, "lon": -88.6680556},
        {"lat": 40.8638889, "lon": -88.6705556},
        {"lat": 40.8638889, "lon": -88.6680556}
    ]
    north_dakota_coords = [
        {"lat": 46.8688889, "lon": -97.2844444},
        {"lat": 46.8686111, "lon": -97.2741667},
        {"lat": 46.8750000, "lon": -97.2741667},
        {"lat": 46.8750000, "lon": -97.2844444}
    ]
    
    if request.method == "POST":
        forecast_type = request.form.get("forecast_type")
        selected_farm = request.form.get("farm")

        if selected_farm == "illinois":
            center_coords = compute_center(illinois_coords)
            tz = pytz.timezone("America/Chicago")
            farm_name = "Farm 1 - Illinois"
        elif selected_farm == "north_dakota":
            center_coords = compute_center(north_dakota_coords)
            tz = pytz.timezone("America/North_Dakota/Center")
            farm_name = "Farm 2 - North Dakota"
        else:
            error = "Invalid farm selection."

        if center_coords and forecast_type:
            try:
                if forecast_type == "hourly":
                    weather = get_weather(center_coords[0], center_coords[1], forecast_type="hourly")
                    current_time = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
                    hourly = weather.get("hourly", {})
                    times = hourly.get("time", [])
                    forecast_data = []
                    for t_str, temp, rh, dp, prec, pp, rn, sh, sn, wc, st0, sm0, ws, wg in zip(
                        times,
                        hourly.get("temperature_2m", []),
                        hourly.get("relative_humidity_2m", []),
                        hourly.get("dew_point_2m", []),
                        hourly.get("precipitation", []),
                        hourly.get("precipitation_probability", []),
                        hourly.get("rain", []),
                        hourly.get("showers", []),
                        hourly.get("snowfall", []),
                        hourly.get("weathercode", []),
                        hourly.get("soil_temperature_0cm", []),
                        hourly.get("soil_moisture_0_to_1cm", []),
                        hourly.get("wind_speed_10m", []),
                        hourly.get("wind_gusts_10m", [])
                    ):
                        try:
                            dt_naive = datetime.fromisoformat(t_str)
                            dt = tz.localize(dt_naive)
                        except Exception:
                            continue
                        if dt >= current_time:
                            forecast_data.append({
                                "time": dt.strftime("%Y-%m-%d %H:%M"),
                                "temperature": temp,
                                "relative_humidity": rh,
                                "dew_point": dp,
                                "precipitation": prec,
                                "precip_prob": pp,
                                "rain": rn,
                                "showers": sh,
                                "snowfall": sn,
                                "weathercode": wc,
                                "weather_icon": map_weather_icon(wc),
                                "soil_temperature_0": st0,
                                "soil_moisture_0": sm0,
                                "wind_speed": ws,
                                "wind_gusts": wg
                            })
                        if len(forecast_data) >= 24:
                            break
                elif forecast_type == "daily":
                    weather = get_weather(center_coords[0], center_coords[1], forecast_type="daily")
                    daily = weather.get("daily", {})
                    forecast_data = []
                    count = 0
                    for t, tmax, tmin, precip_sum, wind_max, uv in zip(
                        daily.get("time", []),
                        daily.get("temperature_2m_max", []),
                        daily.get("temperature_2m_min", []),
                        daily.get("precipitation_sum", []),
                        daily.get("wind_speed_10m_max", []),
                        daily.get("uv_index_max", [])
                    ):
                        forecast_data.append({
                            "date": t,
                            "temp_max": tmax,
                            "temp_min": tmin,
                            "precipitation_sum": precip_sum,
                            "wind_speed_max": wind_max,
                            "uv_index": uv
                        })
                        count += 1
                        if count >= 7:  # Limit to 7 days forecast
                            break
            except Exception as e:
                error = str(e)
            
    now = datetime.now()
    return render_template("dashboard.html",
                           forecast_data=forecast_data,
                           center_coords=center_coords,
                           forecast_type=forecast_type,
                           error=error,
                           farm_name=farm_name,
                           now=now)

img_size = 224

model_path = os.path.join(os.getcwd(), "plant_disease_prediction_model.h5")
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model file not found at: {model_path}")
disease_model = tf.keras.models.load_model(model_path)

class_indices_path = os.path.join(os.getcwd(), "class_indices.pkl")
if not os.path.exists(class_indices_path):
    raise FileNotFoundError(f"Class indices file not found at: {class_indices_path}")
with open(class_indices_path, "rb") as f:
    class_indices = pickle.load(f)

# Determine mapping orientation:
first_key = next(iter(class_indices))
if str(first_key).isdigit():
    class_indices = {int(k): v for k, v in class_indices.items()}
else:
    class_indices = {int(v): k for k, v in class_indices.items()}

print("DEBUG: Loaded class_indices mapping:", class_indices)

def load_and_preprocess_image_from_file(file, target_size=(img_size, img_size)):
    try:
        img = Image.open(file).convert("RGB")
        img = img.resize(target_size)
        img_array = np.array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = img_array.astype("float32") / 255.0
        return img_array
    except Exception as e:
        traceback.print_exc()
        raise e

def predict_disease_from_file(file):
    preprocessed_img = load_and_preprocess_image_from_file(file, target_size=(img_size, img_size))
    predictions = disease_model.predict(preprocessed_img)
    predicted_class_index = np.argmax(predictions, axis=1)[0]
    if predicted_class_index not in class_indices:
        raise KeyError(f"Predicted index {predicted_class_index} not found in class_indices. Full mapping: {class_indices}")
    return class_indices[predicted_class_index]

@app.route("/chatbot")
@login_required
def chatbot():
    # Clear conversation state on refresh so a new session starts
    session.pop("selected_farm_id", None)
    session.pop("selected_farm_introduced", None)
    session.pop("general_started", None)
    session.pop("general_question_asked", None)
    now = datetime.now()
    return render_template("chatbot.html", now=now)

@app.route("/disease", methods=["GET", "POST"])
@login_required
def disease():
    now = datetime.now()
    prediction = None
    image_url = None

    if request.method == "POST":
        file = request.files.get("image")
        if file:
            try:
                filename = secure_filename(file.filename)
                # Ensure the upload directory exists
                os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
                save_path = os.path.join("static", "uploads", filename)
                file.save(save_path)

                with open(save_path, "rb") as f:
                    prediction = predict_disease_from_file(f)

                image_url = url_for("static", filename=f"uploads/{filename}")
            except Exception as e:
                traceback.print_exc()
                prediction = f"Error processing image: {str(e)}"
        else:
            prediction = "No image uploaded."

    return render_template("disease.html", now=now, prediction=prediction, image_url=image_url)

# ------------------------------
# Chatbot Conversation Endpoint
# ------------------------------
@app.route("/get_response", methods=["POST"])
@login_required
def get_response():
    import re
    data = request.get_json()
    user_message = data.get("message", "")
    lower_message = user_message.lower().strip()
    image_base64 = data.get("image", None)
    image_type = data.get("image_type", "image/jpeg")
    
    # ------------------------------
    # Get Dynamic List of Farms for Current User
    # ------------------------------
    user_id = 1  # In production, use session user id
    farms = get_user_farms(user_id)
    available_farms = {str(farm["id"]): farm["name"] for farm in farms}
    farms_list = "\n".join(available_farms.values())
    
    # ------------------------------
    # Determine Conversation Mode
    # ------------------------------
    # If a general conversation is already in progress, use that branch.
    if session.get("general_started"):
        scenario = "general"
    # Else if a specific farm is already selected, use specific branch.
    elif session.get("selected_farm_id"):
        scenario = "specific"
    else:
        # First, check if the user's message exactly matches any available farm names.
        matched_farm = None
        for farm_id, farm_name in available_farms.items():
            if farm_name.lower() == lower_message:
                matched_farm = farm_id
                break
        if matched_farm:
            session["selected_farm_id"] = matched_farm
            session["selected_farm_introduced"] = False
            scenario = "specific"
        # If not an exact match, check for greetings.
        elif any(greet in lower_message for greet in ["hey", "hi", "hello"]):
            return jsonify({"response": "Hello! Would you like general agriculture advice or specific recommendations for one of your farms? Please reply with 'general' for general advice or 'specific' for farm-specific recommendations."})
        # Check if the user mentions 'specific'
        elif "specific" in lower_message:
            # If a farm name isn’t included, list available farms dynamically.
            if not any(farm.lower() in lower_message for farm in available_farms.values()):
                return jsonify({"response": "Please choose a farm from the following list for specific recommendations:\n" + farms_list})
            # If the message includes one of the farm names along with "specific", set that farm.
            for farm_id, farm_name in available_farms.items():
                if farm_name.lower() in lower_message:
                    session["selected_farm_id"] = farm_id
                    session["selected_farm_introduced"] = False
                    scenario = "specific"
                    break
            if not session.get("selected_farm_id"):
                return jsonify({"response": "I couldn't match that farm. Please choose from the list:\n" + farms_list})
        elif "general" in lower_message:
            session["general_started"] = True
            scenario = "general"
        else:
            return jsonify({"response": "Would you like general agriculture advice or specific recommendations for one of your farms? Please reply with 'general' or 'specific'."})
    
    # ------------------------------
    # Build the Prompt Based on the Scenario
    # ------------------------------
    prompt_template = ""
    if scenario == "general":
        # Ask a clarifying question only on the first general query.
        if not session.get("general_question_asked"):
            session["general_question_asked"] = True
            prompt_template = (
                "Let's talk about general agriculture topics. What specific question or topic would you like to discuss? "
                "For example, you can ask about crop production, soil management, or market trends in Illinois and North Dakota."
            )
            return jsonify({"response": prompt_template})
        else:
            prompt_template = "User Query: {user_message}".format(user_message=user_message)
    
    elif scenario == "specific":
        # Retrieve dynamic farm data.
        selected_farm_id = session.get("selected_farm_id")
        # Find the farm in our dynamic list.
        farm = None
        for f in farms:
            if str(f["id"]) == selected_farm_id:
                farm = f
                break
        if farm:
            # Build farm details.
            farm_info = (
                f"Farm Name: {farm['name']}\n"
                f"State: {farm['state']}\n"
                f"Coordinates: ({farm['latitude']}, {farm['longitude']})\n"
                f"Description: {farm['description']}\n"
            )
            # Here you might also want to list equipment dynamically.
            # For demonstration, we assume equipment info is not dynamic.
            if selected_farm_id == "1":
                equipment_info = "Equipment Available: Tractor, Combine\n"
            elif selected_farm_id == "2":
                equipment_info = "Equipment Available: Plow, Harvester\n"
            else:
                equipment_info = ""
            
            # Fetch daily forecast (for next 7 days).
            forecast_info = ""
            try:
                weather_daily = get_weather(farm["latitude"], farm["longitude"], forecast_type="daily")
                daily_data = weather_daily.get("daily", {})
                if daily_data:
                    forecast_info += "Weather Forecast for the Next 7 Days:\n"
                    count = 0
                    for date, tmax, tmin, precip, wind in zip(
                        daily_data.get("time", []),
                        daily_data.get("temperature_2m_max", []),
                        daily_data.get("temperature_2m_min", []),
                        daily_data.get("precipitation_sum", []),
                        daily_data.get("wind_speed_10m_max", [])
                    ):
                        forecast_info += (
                            f"Date: {date}, Temp: {tmin}°C - {tmax}°C, "
                            f"Precipitation: {precip}mm, Wind: {wind} km/h\n"
                        )
                        count += 1
                        if count >= 7:
                            break
                else:
                    forecast_info += "No daily forecast data available.\n"
            except Exception as e:
                forecast_info += f"Error retrieving daily forecast data: {str(e)}\n"
            
            # Add state-specific context.
            state_lower = farm["state"].lower()
            if "illinois" in state_lower:
                farm_context = (
                    "Regional Context (Illinois):\n"
                    "- Consider minimal tillage to reduce soil erosion due to periodic dust storms.\n"
                    "- Cover crops and soil conservation practices are recommended.\n"
                    "- AI recommendation: Evaluate no-till options if moisture is adequate."
                )
            elif "north dakota" in state_lower:
                farm_context = (
                    "Regional Context (North Dakota):\n"
                    "- Soil moisture and composition are critical; consider no-till or strip-till practices.\n"
                    "- Equipment cleaning is important to prevent soil compaction.\n"
                    "- AI recommendation: Use precision agriculture techniques to optimize inputs."
                )
            else:
                farm_context = f"Regional context for {farm['state']} is not specifically defined."
            
            if not session.get("selected_farm_introduced"):
                prompt_template = (
                    "Great, let's talk about this farm!\n\n"
                    "Here are the details:\n"
                    "{farm_info}\n"
                    "{equipment_info}"
                    "{forecast_info}\n"
                    "{farm_context}\n\n"
                    "Based on the above conditions for the next week, would you like to know my recommendation "
                    "or do you have a specific question about this farm?\n"
                    "User Query: {user_message}"
                ).format(
                    farm_info=farm_info,
                    equipment_info=equipment_info,
                    forecast_info=forecast_info,
                    farm_context=farm_context,
                    user_message=user_message
                )
                session["selected_farm_introduced"] = True
            else:
                prompt_template = (
                    "Recall we are discussing the following farm:\n"
                    "{farm_info}\n"
                    "{equipment_info}"
                    "{forecast_info}\n"
                    "{farm_context}\n\n"
                    "Please answer the following question based on the above conditions: {user_message}"
                ).format(
                    farm_info=farm_info,
                    equipment_info=equipment_info,
                    forecast_info=forecast_info,
                    farm_context=farm_context,
                    user_message=user_message
                )
        else:
            prompt_template = (
                "That farm doesn't exist. Please choose a valid option from the list:\n" + farms_list +
                "\n\nUser Query: {user_message}"
            ).format(user_message=user_message)
    
    else:
        prompt_template = (
            "Would you like general agriculture advice or specific recommendations for one of your farms? "
            "Please reply with 'general' or 'specific'.\n\n"
            "User Query: {user_message}"
        ).format(user_message=user_message)
    
    # ------------------------------
    # Build the Message for the AI Model
    # ------------------------------
    message_content = [{"type": "text", "text": prompt_template}]
    if image_base64:
        image_data_url = f"data:{image_type};base64,{image_base64}"
        message_content.append({
            "type": "image_url",
            "image_url": {"url": image_data_url, "detail": "auto"}
        })
    
    messages = [{"role": "user", "content": message_content}]
    
    try:
        selected_model = endpoints["gpt_40"]
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            max_completion_tokens=1000,
        )
        app.logger.debug("AzureOpenAI API response for model %s: %s", selected_model, response)
        message_content_response = None
        if response.choices and hasattr(response.choices[0], "message"):
            message_content_response = response.choices[0].message.content
        else:
            app.logger.debug("Unexpected response structure for model %s: %s", selected_model, response)
        if not message_content_response:
            app.logger.debug("Blank text received in API response for model %s.", selected_model)
        final_response = message_content_response or ""
    except Exception as e:
        final_response = "Sorry, I encountered an error: " + str(e)
        app.logger.error("Error during API call: %s", e)
    
    return jsonify({"response": final_response})

# ------------------------------
# Speech-to-Text Route
# ------------------------------
@app.route("/speech_to_text", methods=["POST"])
@login_required
def speech_to_text():
    data = request.get_json()
    audio_base64 = data.get("audio", None)
    if not audio_base64:
        return jsonify({"error": "No audio provided"}), 400

    # Decode the base64 audio data
    audio_bytes = base64.b64decode(audio_base64)

    # Convert the audio bytes to a WAV file using pydub
    try:
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        temp_filename = "temp_audio.wav"
        audio_segment.export(temp_filename, format="wav")
    except Exception as e:
        return jsonify({"error": "Failed to process audio: " + str(e)}), 500

    # Use SpeechRecognition to transcribe the audio
    r = sr.Recognizer()
    try:
        with sr.AudioFile(temp_filename) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)
    except sr.UnknownValueError:
        text = ""
    except Exception as e:
        text = ""
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    return jsonify({"text": text})

if __name__ == "__main__":
    app.run(debug=True)
