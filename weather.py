import requests
import pytz
from datetime import datetime

def compute_center(coordinates):
    """
    Compute the center latitude and longitude from a list of coordinate dicts.
    """
    lats = [coord["lat"] for coord in coordinates]
    lons = [coord["lon"] for coord in coordinates]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2
    return center_lat, center_lon

def get_weather(latitude, longitude, forecast_type="hourly"):
    """
    Fetch weather data from the Open-Meteo API.
    """
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
            "soil_temperature_0cm,wind_speed_10m,wind_gusts_10m"
        )
    elif forecast_type == "daily":
        params["daily"] = (
            "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,uv_index_max"
        )
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    return response.json()

def get_optimal_weather_icon(weathercode, timezone_str="America/Chicago"):
    """
    Returns the optimal weather icon filename based on the weather code and current local time.
    If it's nighttime (before 6 AM or at/after 6 PM), returns 'night.png';
    otherwise returns an icon based on the weather code.
    
    The available icon filenames (placed in static/icons/) are:
      - default.png
      - drizzle.png
      - fog.png
      - logo.png, logo2.png  (for branding; not used here)
      - partly_cloudy.png
      - rain.png
      - snow.png
      - sun.png
      - thunderstrom.png
      - night.png   <-- must exist for nighttime display
    """
    tz = pytz.timezone(timezone_str)
    current_time = datetime.now(tz)
    
    # Nighttime: before 6 AM or 6 PM and after
    if current_time.hour < 6 or current_time.hour >= 18:
        return "night.png"
    
    # Daytime icon selection based on weathercode
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
        return "thunderstrom.png"
    else:
        return "default.png"

def get_hourly_forecast(name, coordinates, timezone_str="America/Chicago"):
    """
    Fetches and returns a list of hourly forecast entries for the next 24 hours.
    Each entry is a dictionary with:
      time, temperature, relative_humidity, dew_point, precipitation, precip_prob,
      rain, showers, snowfall, weathercode, weather_icon, soil_temperature_0, wind_speed, wind_gusts
    """
    center_lat, center_lon = compute_center(coordinates)
    tz = pytz.timezone(timezone_str)
    current_time = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    
    weather = get_weather(center_lat, center_lon, forecast_type="hourly")
    hourly = weather.get("hourly", {})
    
    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    rel_humidities = hourly.get("relative_humidity_2m", [])
    dew_points = hourly.get("dew_point_2m", [])
    precipitations = hourly.get("precipitation", [])
    precip_probs = hourly.get("precipitation_probability", [])
    rains = hourly.get("rain", [])
    showers = hourly.get("showers", [])
    snowfalls = hourly.get("snowfall", [])
    weather_codes = hourly.get("weathercode", [])
    soil_temp_0 = hourly.get("soil_temperature_0cm", [])
    wind_speeds = hourly.get("wind_speed_10m", [])
    wind_gusts = hourly.get("wind_gusts_10m", [])
    
    forecast = []
    for t_str, temp, rh, dp, prec, pp, rn, sh, sn, wc, st0, ws, wg in zip(
        times, temperatures, rel_humidities, dew_points, precipitations, precip_probs,
        rains, showers, snowfalls, weather_codes, soil_temp_0, wind_speeds, wind_gusts
    ):
        try:
            dt_naive = datetime.fromisoformat(t_str)
            dt = tz.localize(dt_naive)
        except Exception:
            continue
        if dt >= current_time:
            icon = get_optimal_weather_icon(wc, timezone_str)
            forecast.append({
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
                "weather_icon": icon,
                "soil_temperature_0": st0,
                "wind_speed": ws,
                "wind_gusts": wg
            })
        if len(forecast) >= 24:
            break
    return forecast

def get_daily_forecast(name, coordinates):
    """
    Fetches and returns a list of daily forecast entries for the next 7 days.
    Each entry is a dictionary with:
      date, temp_max, temp_min, precipitation_sum, wind_speed_max, uv_index
    Note: For daily forecasts, dynamic icons are not computed in this example.
    """
    center_lat, center_lon = compute_center(coordinates)
    weather = get_weather(center_lat, center_lon, forecast_type="daily")
    daily = weather.get("daily", {})
    
    times = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])
    precip_sum = daily.get("precipitation_sum", [])
    wind_max = daily.get("wind_speed_10m_max", [])
    uv_index = daily.get("uv_index_max", [])
    
    forecast = []
    for t, tmax, tmin, precip, wind, uv in zip(times, temp_max, temp_min, precip_sum, wind_max, uv_index):
        forecast.append({
            "date": t,
            "temp_max": tmax,
            "temp_min": tmin,
            "precipitation_sum": precip,
            "wind_speed_max": wind,
            "uv_index": uv
        })
        if len(forecast) >= 7:
            break
    return forecast

if __name__ == "__main__":
    # Example usage for testing:
    illinois_coords = [
        {"lat": 40.8663889, "lon": -88.6705556},
        {"lat": 40.8663889, "lon": -88.6680556},
        {"lat": 40.8638889, "lon": -88.6705556},
        {"lat": 40.8638889, "lon": -88.6680556}
    ]
    print("Hourly Forecast for PTI Farm Illinois:")
    hourly = get_hourly_forecast("PTI Farm Illinois", illinois_coords, "America/Chicago")
    for entry in hourly:
        print(entry)
    
    print("\nDaily Forecast for PTI Farm Illinois:")
    daily = get_daily_forecast("PTI Farm Illinois", illinois_coords)
    for entry in daily:
        print(entry)
