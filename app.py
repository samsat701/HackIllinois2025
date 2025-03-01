import os
import sqlite3
import markdown
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

# --- Gemini integration removed ---
# from google import genai
# gemini_api_key = os.getenv("GEMINI_API_KEY")
# client = genai.Client(api_key=gemini_api_key)

# --- Azure OpenAI integration ---
from openai import AzureOpenAI

# Get the API key and endpoint from the .env file
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

    # Define farm coordinates
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
                    times = daily.get("time", [])
                    forecast_data = []
                    for t, tmax, tmin, precip_sum, wind_max, uv in zip(
                        times,
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

@app.route("/chatbot")
@login_required
def chatbot():
    now = datetime.now()
    return render_template("chatbot.html", now=now)

@app.route("/get_response", methods=["POST"])
@login_required
def get_response():
    data = request.get_json()
    user_message = data.get("message", "")
    image_base64 = data.get("image", None)
    image_type = data.get("image_type", "image/jpeg")  # default to JPEG if not provided

    # Construct the text prompt
    text_prompt = f"You are an expert agriculture specialist named Randy.\n{user_message}"
    
    # Build the messages content array:
    message_content = [{"type": "text", "text": text_prompt}]
    if image_base64:
        # Build the data URL for the image
        image_data_url = f"data:{image_type};base64,{image_base64}"
        message_content.append({
            "type": "image_url",
            "image_url": {"url": image_data_url, "detail": "auto"}
        })

    messages = [{"role": "user", "content": message_content}]
    
    try:
        # Select model based on presence of image input
        if image_base64:
            selected_model = endpoints["gpt_40"]
        else:
            #selected_model = endpoints["gpt_o1_mini"]
            selected_model = endpoints["gpt_40"]
        
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            max_completion_tokens=300,
        )
        
        # Log the raw API response for debugging
        app.logger.debug("AzureOpenAI API response for model %s: %s", selected_model, response)
        print("DEBUG: API response for model", selected_model, ":", response)
        
        # Extract the message content
        message_content_response = None
        if response.choices and hasattr(response.choices[0], "message"):
            message_content_response = response.choices[0].message.content
        else:
            app.logger.debug("Response structure unexpected for model %s: %s", selected_model, response)
            print("DEBUG: Unexpected response structure for model", selected_model, ":", response)
        
        # Log if blank text is received
        if not message_content_response:
            app.logger.debug("Blank text received in API response for model %s. Full response: %s", selected_model, response)
            print("DEBUG: Blank text received for model", selected_model, "Full response:", response)
        
        final_response = convert_markdown(message_content_response or "")
    except Exception as e:
        final_response = "Sorry, I encountered an error: " + str(e)
        app.logger.error("Error during API call: %s", e)
        print("DEBUG: Exception occurred:", e)
    
    return jsonify({"response": final_response})

if __name__ == "__main__":
    app.run(debug=True)
