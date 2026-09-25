import requests
import time
from datetime import datetime

LAT=25.0330
LON=121.5654
TIMEZONE="Asia/Taipei"


def _get_json(params):
    """Fetch forecast with short retries so one transient API error does not kill publishing."""
    url="https://api.open-meteo.com/v1/forecast"
    last_error=None
    for attempt in range(5):
        try:
            response=requests.get(url,params=params,timeout=(10,45))
            response.raise_for_status()
            data=response.json()
            if not isinstance(data,dict):
                raise RuntimeError("Weather API returned invalid JSON")
            return data
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error=exc
            if attempt < 4:
                time.sleep(5*(attempt+1))
    raise RuntimeError(f"Weather API failed after 5 attempts: {last_error}")


def get_weather():
    """Morning/daytime weather. Kept unchanged for the existing 07:00 flow."""
    data=_get_json({
        "latitude":LAT,
        "longitude":LON,
        "daily":"weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone":TIMEZONE,
        "forecast_days":1,
    })["daily"]
    return {
        "date":data["time"][0],
        "code":data["weather_code"][0],
        "high":round(data["temperature_2m_max"][0]),
        "low":round(data["temperature_2m_min"][0]),
        "rain":data["precipitation_probability_max"][0],
    }


def get_evening_weather():
    """Weather for the 17:00 evening edition.

    - condition: representative 17:00 weather code
    - temperature: forecast temperature at 17:00
    - low: minimum forecast temperature from 17:00 through 23:00
    - rain: maximum precipitation probability from 17:00 through 23:00

    This function is intentionally separate from get_weather() so the existing
    morning production path remains unchanged until the evening flow is tested.
    """
    data=_get_json({
        "latitude":LAT,
        "longitude":LON,
        "hourly":"temperature_2m,precipitation_probability,weather_code",
        "timezone":TIMEZONE,
        "forecast_days":1,
    })["hourly"]

    rows=[]
    for time_text,temp,rain,code in zip(
        data["time"],
        data["temperature_2m"],
        data["precipitation_probability"],
        data["weather_code"],
    ):
        hour=datetime.fromisoformat(time_text).hour
        if 17 <= hour <= 23:
            rows.append((time_text,temp,rain,code))

    if not rows:
        raise RuntimeError("No 17:00-23:00 hourly forecast returned by Open-Meteo")

    at_17=next((row for row in rows if datetime.fromisoformat(row[0]).hour==17),rows[0])
    return {
        "date":at_17[0][:10],
        "code":at_17[3],
        "temperature":round(at_17[1]),
        # Keep 'high' for compatibility with the current theme/temperature helpers.
        "high":round(at_17[1]),
        "low":round(min(row[1] for row in rows)),
        "rain":max(row[2] for row in rows),
        "period":"evening",
        "window":"17:00-23:00",
    }


if __name__=="__main__":
    print("Morning:",get_weather())
    print("Evening:",get_evening_weather())
