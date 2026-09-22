import requests

LAT=25.0330
LON=121.5654

def get_weather():
    url="https://api.open-meteo.com/v1/forecast"
    params={"latitude":LAT,"longitude":LON,"daily":"weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max","timezone":"Asia/Taipei","forecast_days":1}
    d=requests.get(url,params=params,timeout=30).json()["daily"]
    return {"date":d["time"][0],"code":d["weather_code"][0],"high":round(d["temperature_2m_max"][0]),"low":round(d["temperature_2m_min"][0]),"rain":d["precipitation_probability_max"][0]}

if __name__=="__main__": print(get_weather())
