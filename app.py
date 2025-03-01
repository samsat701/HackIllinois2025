from flask import Flask, render_template, request, url_for
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

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
            "soil_temperature_0cm,soil_temperature_6cm,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,"
            "wind_speed_10m,wind_gusts_10m"
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
        {"lat": 46.8688889, "lon": -97.2844444},  # 46°52'08"N, 97°17'04"W
        {"lat": 46.8686111, "lon": -97.2741667},  # 46°52'07"N, 97°16'27"W
        {"lat": 46.8750000, "lon": -97.2741667},  # 46°52'30"N, 97°16'27"W
        {"lat": 46.8750000, "lon": -97.2844444}   # 46°52'30"N, 97°17'04"W
    ]
    
    if request.method == "POST":
        forecast_type = request.form.get("forecast_type")
        try:
            center_coords = compute_center(illinois_coords)
            if forecast_type == "hourly":
                weather = get_weather(center_coords[0], center_coords[1], forecast_type="hourly")
                tz = pytz.timezone("America/Chicago")
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
            
    # Pass the current date/time to the template using "now"
    now = datetime.now()
    return render_template("dashboard.html",
                           forecast_data=forecast_data,
                           center_coords=center_coords,
                           forecast_type=forecast_type,
                           error=error,
                           now=now)

@app.route("/chatbot")
def chatbot():
    now = datetime.now()
    return render_template("chatbot.html", now=now)

if __name__ == "__main__":
    app.run(debug=True)
