import os
import markdown
from dotenv import load_dotenv
load_dotenv()

from google import genai

# Initialize Gemini client using API key from the .env file
gemini_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key)

from flask import Flask, render_template, request, jsonify, url_for
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

def convert_markdown(md_text):
    """
    Convert Markdown text to HTML with additional extensions.
    """
    # Use extensions for better formatting
    return markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'nl2br'])

# (Existing functions for weather and coordinates remain unchanged)
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

@app.route("/")
def home():
    now = datetime.now()
    return render_template("home.html", now=now)

@app.route("/weather", methods=["GET", "POST"])
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
        selected_farm = request.form.get("farm")  # Read farm from the hidden input

        # Determine which farm is selected and set timezone accordingly
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
def chatbot():
    now = datetime.now()
    return render_template("chatbot.html", now=now)

@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json()
    user_message = data.get("message", "")
    
    prompt = f"""
You are an expert agriculture specialist named Randy.
{user_message}
"""
    try:
        # Using Gemini API instead of OpenAI:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        # Convert Markdown response to HTML so formatting is preserved
        final_response = convert_markdown(response.text)
    except Exception as e:
        final_response = "Sorry, I encountered an error: " + str(e)
    
    return jsonify({"response": final_response})

if __name__ == "__main__":
    app.run(debug=True)
