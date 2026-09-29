import os
import time
from datetime import datetime

import requests

from city_config import load_city_config


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


def _cwa_code(text):
    text=(text or "").replace(" ","")
    if "雷" in text: return 95
    if "雨" in text: return 61
    if "陰" in text: return 3
    if "雲" in text: return 2
    return 0


def _cwa_weather(city, evening=False):
    if city.get("id") != "taipei":
        raise RuntimeError("CWA fallback is only configured for Taipei")
    key=os.environ.get("CWA_API_KEY")
    if not key:
        raise RuntimeError("CWA_API_KEY is not configured")
    url="https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
    r=requests.get(
        url,
        params={"Authorization":key,"locationName":"臺北市","format":"JSON"},
        timeout=(10,45),
    )
    r.raise_for_status()
    loc=r.json()["records"]["location"][0]
    elements={x["elementName"]:x["time"] for x in loc["weatherElement"]}
    idx=1 if evening and len(elements["Wx"])>1 else 0
    wx=elements["Wx"][idx]["parameter"]["parameterName"]
    pop=int(elements["PoP"][idx]["parameter"]["parameterName"])
    low=int(elements["MinT"][idx]["parameter"]["parameterName"])
    high=int(elements["MaxT"][idx]["parameter"]["parameterName"])
    date=elements["Wx"][idx]["startTime"][:10]
    if evening:
        return {
            "date":date,
            "code":_cwa_code(wx),
            "temperature":high,
            "high":high,
            "low":low,
            "rain":pop,
            "period":"evening",
            "window":"CWA 12-hour forecast",
            "source":"CWA",
            "city":city["id"],
        }
    return {
        "date":date,
        "code":_cwa_code(wx),
        "high":high,
        "low":low,
        "rain":pop,
        "period":"morning",
        "window":"CWA 12-hour forecast",
        "source":"CWA",
        "city":city["id"],
    }


def _open_meteo_hourly(city):
    return _get_json({
        "latitude":city["latitude"],
        "longitude":city["longitude"],
        "hourly":"temperature_2m,precipitation_probability,weather_code",
        "timezone":city["timezone"],
        "forecast_days":1,
    })["hourly"]


def get_weather(city=None):
    """Morning/daytime forecast using the selected city's local timezone."""
    city=city or load_city_config()
    start_hour,end_hour=city.get("morning_window",[7,17])
    try:
        data=_open_meteo_hourly(city)
    except Exception as exc:
        if city.get("weather_fallback")=="cwa":
            print(f"Open-Meteo morning failed; falling back to CWA: {exc}")
            return _cwa_weather(city,False)
        raise

    rows=[]
    for time_text,temp,rain,code in zip(
        data["time"],
        data["temperature_2m"],
        data["precipitation_probability"],
        data["weather_code"],
    ):
        hour=datetime.fromisoformat(time_text).hour
        if start_hour <= hour <= end_hour:
            rows.append((time_text,temp,rain,code))

    if not rows:
        raise RuntimeError(f"No {start_hour:02d}:00-{end_hour:02d}:00 hourly forecast returned by Open-Meteo")

    counts={}
    for row in rows:
        counts[row[3]]=counts.get(row[3],0)+1
    representative_code=min(counts, key=lambda code: (-counts[code], code))
    print(
        f"{city['display_name']} morning hourly weather codes:",
        [(datetime.fromisoformat(r[0]).hour, r[3]) for r in rows],
    )
    print("Morning representative weather code:",representative_code,"counts:",counts)

    return {
        "date":rows[0][0][:10],
        "code":representative_code,
        "high":round(max(row[1] for row in rows)),
        "low":round(min(row[1] for row in rows)),
        "rain":max(row[2] for row in rows),
        "period":"morning",
        "window":f"{start_hour:02d}:00-{end_hour:02d}:00",
        "source":"Open-Meteo",
        "city":city["id"],
    }


def get_evening_weather(city=None):
    """Evening forecast using the selected city's local timezone."""
    city=city or load_city_config()
    start_hour,end_hour=city.get("evening_window",[17,23])
    try:
        data=_open_meteo_hourly(city)
    except Exception as exc:
        if city.get("weather_fallback")=="cwa":
            print(f"Open-Meteo evening failed; falling back to CWA: {exc}")
            return _cwa_weather(city,True)
        raise

    rows=[]
    for time_text,temp,rain,code in zip(
        data["time"],
        data["temperature_2m"],
        data["precipitation_probability"],
        data["weather_code"],
    ):
        hour=datetime.fromisoformat(time_text).hour
        if start_hour <= hour <= end_hour:
            rows.append((time_text,temp,rain,code))

    if not rows:
        raise RuntimeError(f"No {start_hour:02d}:00-{end_hour:02d}:00 hourly forecast returned by Open-Meteo")

    at_start=next(
        (row for row in rows if datetime.fromisoformat(row[0]).hour==start_hour),
        rows[0],
    )
    return {
        "date":at_start[0][:10],
        "code":at_start[3],
        "temperature":round(at_start[1]),
        "high":round(at_start[1]),
        "low":round(min(row[1] for row in rows)),
        "rain":max(row[2] for row in rows),
        "period":"evening",
        "window":f"{start_hour:02d}:00-{end_hour:02d}:00",
        "source":"Open-Meteo",
        "city":city["id"],
    }


if __name__=="__main__":
    city=load_city_config()
    print("City:",city["id"])
    print("Morning:",get_weather(city))
    print("Evening:",get_evening_weather(city))
