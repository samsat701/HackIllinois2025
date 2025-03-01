import requests
from datetime import datetime
import pytz

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

def print_hourly_forecast(name, coordinates):
    center_lat, center_lon = compute_center(coordinates)
    print(f"{name} Center Coordinates:")
    print(f"  Latitude:  {center_lat:.6f}")
    print(f"  Longitude: {center_lon:.6f}\n")
    
    tz = pytz.timezone("America/Chicago")
    current_time = datetime.now(tz)
    current_hour = current_time.replace(minute=0, second=0, microsecond=0)
    print("Current local date and time in Illinois:")
    print(f"  {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    weather = get_weather(center_lat, center_lon, forecast_type="hourly")
    hourly = weather.get("hourly", {})
    
    times = hourly.get("time", [])
    temperature = hourly.get("temperature_2m", [])
    rel_humidity = hourly.get("relative_humidity_2m", [])
    dew_point = hourly.get("dew_point_2m", [])
    precipitation = hourly.get("precipitation", [])
    precip_prob = hourly.get("precipitation_probability", [])
    rain = hourly.get("rain", [])
    showers = hourly.get("showers", [])
    snowfall = hourly.get("snowfall", [])
    weather_code = hourly.get("weathercode", [])
    soil_temp_0 = hourly.get("soil_temperature_0cm", [])
    soil_temp_6 = hourly.get("soil_temperature_6cm", [])
    soil_moisture_0 = hourly.get("soil_moisture_0_to_1cm", [])
    soil_moisture_1 = hourly.get("soil_moisture_1_to_3cm", [])
    wind_speed = hourly.get("wind_speed_10m", [])
    wind_gusts = hourly.get("wind_gusts_10m", [])
    
    forecast = []
    for t_str, temp, rh, dp, prec, pp, rn, sh, sn, wc, st0, st6, sm0, sm1, ws, wg in zip(
        times, temperature, rel_humidity, dew_point, precipitation, precip_prob,
        rain, showers, snowfall, weather_code, soil_temp_0, soil_temp_6,
        soil_moisture_0, soil_moisture_1, wind_speed, wind_gusts
    ):
        try:
            dt_naive = datetime.fromisoformat(t_str)
            dt = tz.localize(dt_naive)
        except Exception:
            continue
        if dt >= current_hour:
            forecast.append({
                "time": dt,
                "temperature": temp,
                "rel_humidity": rh,
                "dew_point": dp,
                "precipitation": prec,
                "precip_prob": pp,
                "rain": rn,
                "showers": sh,
                "snowfall": sn,
                "weathercode": wc,
                "soil_temp_0": st0,
                "soil_temp_6": st6,
                "soil_moisture_0": sm0,
                "soil_moisture_1": sm1,
                "wind_speed": ws,
                "wind_gusts": wg
            })
        if len(forecast) >= 24:
            break

    if forecast:
        header = (
            f"{'Time':<16}{'Temp':<6}{'RH':<4}{'DP':<6}{'Prec':<6}{'P%':<4}"
            f"{'Rain':<6}{'Showers':<8}{'Snow':<6}{'WC':<4}{'SoilT0':<8}"
            f"{'SoilT6':<8}{'SoilM0':<8}{'SoilM1':<8}{'WSpd':<6}{'WGust':<6}"
        )
        print("Hourly Forecast for the Next 24 Hours:")
        print(header)
        print("-" * len(header))
        for entry in forecast:
            print(
                f"{entry['time'].strftime('%H:%M'):<16}"
                f"{entry['temperature']:<6}{entry['rel_humidity']:<4}{entry['dew_point']:<6}"
                f"{entry['precipitation']:<6}{entry['precip_prob']:<4}"
                f"{entry['rain']:<6}{entry['showers']:<8}{entry['snowfall']:<6}"
                f"{entry['weathercode']:<4}{entry['soil_temp_0']:<8}"
                f"{entry['soil_temp_6']:<8}{entry['soil_moisture_0']:<8}"
                f"{entry['soil_moisture_1']:<8}{entry['wind_speed']:<6}{entry['wind_gusts']:<6}"
            )
    else:
        print("No hourly forecast data available.")

def print_daily_forecast(name, coordinates):
    center_lat, center_lon = compute_center(coordinates)
    print(f"{name} Center Coordinates:")
    print(f"  Latitude:  {center_lat:.6f}")
    print(f"  Longitude: {center_lon:.6f}\n")
    
    weather = get_weather(center_lat, center_lon, forecast_type="daily")
    daily = weather.get("daily", {})
    
    times = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])
    precip_sum = daily.get("precipitation_sum", [])
    wind_max = daily.get("wind_speed_10m_max", [])
    uv_index = daily.get("uv_index_max", [])
    
    if times:
        header = f"{'Date':<12}{'MaxT (°C)':<10}{'MinT (°C)':<10}{'Precip (mm)':<12}{'WindMax (km/h)':<16}{'UV Index':<8}"
        print("Daily Forecast for the Next 7 Days:")
        print(header)
        print("-" * len(header))
        for t, tmax, tmin, precip, wind, uv in zip(times, temp_max, temp_min, precip_sum, wind_max, uv_index):
            print(f"{t:<12}{tmax:<10}{tmin:<10}{precip:<12}{wind:<16}{uv:<8}")
    else:
        print("No daily forecast data available.")

def main():
    illinois_coords = [
        {"lat": 40.8663889, "lon": -88.6705556},  # 40°51'59"N, 88°40'14"W
        {"lat": 40.8663889, "lon": -88.6680556},  # 40°51'59"N, 88°40'05"W
        {"lat": 40.8638889, "lon": -88.6705556},  # 40°51'50"N, 88°40'14"W
        {"lat": 40.8638889, "lon": -88.6680556}   # 40°51'50"N, 88°40'05"W
    ]
    
    north_dakota_coords = [
        {"lat": 46.8688889, "lon": -97.2844444},  # 46°52'08"N, 97°17'04"W
        {"lat": 46.8686111, "lon": -97.2741667},  # 46°52'07"N, 97°16'27"W
        {"lat": 46.8750000, "lon": -97.2741667},  # 46°52'30"N, 97°16'27"W
        {"lat": 46.8750000, "lon": -97.2844444}   # 46°52'30"N, 97°17'04"W
    ]
    
    print("Choose forecast type:")
    print("1. Hourly Forecast (Next 24 Hours)")
    print("2. Daily Forecast (Next 7 Days)")
    choice = input("Enter 1 or 2: ").strip()
    
    if choice == "1":
        print_hourly_forecast("PTI Farm Illinois", illinois_coords)
    elif choice == "2":
        print_daily_forecast("PTI Farm Illinois", illinois_coords)
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
