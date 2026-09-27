import requests
import time
import os
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



def _cwa_code(text):
    text=(text or "").replace(" ","")
    if "雷" in text: return 95
    if "雨" in text: return 61
    if "陰" in text: return 3
    if "雲" in text: return 2
    return 0

def _cwa_weather(evening=False):
    key=os.environ.get("CWA_API_KEY")
    if not key:
        raise RuntimeError("CWA_API_KEY is not configured")
    url="https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
    r=requests.get(url,params={"Authorization":key,"locationName":"臺北市","format":"JSON"},timeout=(10,45))
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
        return {"date":date,"code":_cwa_code(wx),"temperature":high,"high":high,"low":low,"rain":pop,"period":"evening","window":"CWA 12-hour forecast","source":"CWA"}
    return {"date":date,"code":_cwa_code(wx),"high":high,"low":low,"rain":pop,"source":"CWA"}


def get_weather():
    """Morning/daytime weather using hourly weather codes from 07:00-17:00.

    The representative condition is the most frequent hourly WMO weather code
    in the daytime window. Ties prefer the clearer/lower code. Temperature
    high/low and rain probability are also derived from the same window.
    """
    try:
        data=_get_json({
            "latitude":LAT,
            "longitude":LON,
            "hourly":"temperature_2m,precipitation_probability,weather_code",
            "timezone":TIMEZONE,
            "forecast_days":1,
        })["hourly"]
    except Exception as exc:
        print(f"Open-Meteo morning failed; falling back to CWA: {exc}")
        return _cwa_weather(False)

    rows=[]
    for time_text,temp,rain,code in zip(
        data["time"],
        data["temperature_2m"],
        data["precipitation_probability"],
        data["weather_code"],
    ):
        hour=datetime.fromisoformat(time_text).hour
        if 7 <= hour <= 17:
            rows.append((time_text,temp,rain,code))

    if not rows:
        raise RuntimeError("No 07:00-17:00 hourly forecast returned by Open-Meteo")

    counts={}
    for row in rows:
        counts[row[3]]=counts.get(row[3],0)+1
    representative_code=min(counts, key=lambda code: (-counts[code], code))
    print("Morning hourly weather codes:", [(datetime.fromisoformat(r[0]).hour, r[3]) for r in rows])
    print("Morning representative weather code:", representative_code, "counts:", counts)

    return {
        "date":rows[0][0][:10],
        "code":representative_code,
        "high":round(max(row[1] for row in rows)),
        "low":round(min(row[1] for row in rows)),
        "rain":max(row[2] for row in rows),
        "period":"morning",
        "window":"07:00-17:00",
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
    try:
        data=_get_json({
            "latitude":LAT,
            "longitude":LON,
            "hourly":"temperature_2m,precipitation_probability,weather_code",
            "timezone":TIMEZONE,
            "forecast_days":1,
        })["hourly"]
    except Exception as exc:
        print(f"Open-Meteo evening failed; falling back to CWA: {exc}")
        return _cwa_weather(True)

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
