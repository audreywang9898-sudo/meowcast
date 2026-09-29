import json
import os
import requests

from city_config import load_city_config

CONFIG_PATH = "config.json"


def load_config():
    defaults = {
        "isAI": False,
        "aiModel": "gpt-5.6-luna",
        "bilingual": True,
        "timezone": "Asia/Taipei",
    }
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            defaults.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Config fallback: {exc}")
    return defaults


def theme(w):
    """Primary sky condition only; temperature is a separate label."""
    if w["rain"] >= 50 or w["code"] >= 51:
        return "rainy"
    if w["code"] in (0, 1, 2):
        return "sunny"
    return "cloudy"


def temperature_label(w):
    """Secondary temperature label based on the day's forecast high."""
    if w["high"] >= 32:
        return "Hot"
    if w["high"] <= 18:
        return "Cold"
    return ""


LINES = {
    "sunny": ("sunny", "晴朗"),
    "rainy": ("rainy with showers", "有雨，可能有陣雨"),
    "cloudy": ("cloudy", "多雲"),
}


def _tags(city, extras=""):
    base=" ".join(city.get("hashtags",[]))
    return (base + extras).strip()


def _simple_english_caption(w, city, event=None):
    t=theme(w)
    en_condition,_=LINES[t]
    date=w["date"].replace("-","/")
    name=city["display_name"]
    cat=city["cat_name"]
    brand=city.get("brand",f"{name} Meowcast")
    country=city.get("country","")
    is_evening=w.get("period")=="evening"

    seasonal=""
    extra_tags=""
    if event:
        event_name=event.get("name_en","")
        note=event.get("caption_en") or event.get("note_en","")
        if event_name:
            seasonal=f"🐾 {event_name} in {name}\n"
            if note:
                seasonal+=f"{note}\n"
            seasonal+="\n"
            safe_tag=event_name.replace(" ","").replace("'","").replace("/","")
            extra_tags+=f" #{safe_tag}"

    if is_evening:
        main_temp=w.get("temperature",w["high"])
        return t, f"""Hi, I’m {cat}! 🐱
The city is winding down — here’s your little weather note for tonight.

{date} {name} Evening Weather 🌙 📍 {brand}

🌙 Tonight’s Weather
📍 {name}, {country}
🌡️ Around 17:00: {main_temp}°C / Tonight’s low {w['low']}°C
🌧️ Highest rain chance this evening: {w['rain']}%
This evening is {en_condition}.

🐾 {cat}’s evening note
As {name} slows down for the night, the light changes, the streets cool, and the city finds a different rhythm.
Whether you’re heading home or taking one last walk, I hope your evening feels calm and cozy. 💛

Have a lovely evening in {name}. 🌙

{_tags(city)}"""

    return t, f"""Hi, I’m {cat}! 🐱
Exploring {name} with you, one little adventure and one weather forecast at a time.

{seasonal}{date} {name} Weather 📍 {brand}

🌤️ Today’s Weather
📍 {name}, {country}
🌡️ High {w['high']}°C / Low {w['low']}°C
🌧️ Rain chance: {w['rain']}%
Today is {en_condition}.

🐾 {cat}’s little note
Weather changes a city in tiny ways — the light, the breeze, the pace of a walk, even where a cat chooses to sit.
Whatever the sky looks like today, I hope you find one small corner of {name} that feels good to you. 💛

Have a lovely day in {name}.

{_tags(city,extra_tags)}"""


def _simple_taipei_caption(w, city, event=None):
    t=theme(w)
    en_condition,zh_condition=LINES[t]
    date=w["date"].replace("-","/")
    rain=w["rain"]
    is_evening=w.get("period")=="evening"

    seasonal_en=""
    seasonal_zh=""
    seasonal_tags=""
    if event:
        name_en=event.get("name_en","")
        name_zh=event.get("name_zh","")
        note_en=event.get("caption_en") or event.get("note_en","")
        note_zh=event.get("caption_zh","")
        event_type=event.get("type","")
        if name_en:
            seasonal_en=f"🐾 {name_en} in Taipei\n"
            if note_en:
                seasonal_en+=f"{note_en}\n"
            seasonal_en+="\n"
        if name_zh:
            seasonal_zh=f"🐱 台北・{name_zh}\n"
            if note_zh:
                seasonal_zh+=f"{note_zh}\n"
            else:
                seasonal_zh+=f"今天是{name_zh}，讓台北貓陪你一起感受今天的小小節日／季節氣氛。\n"
            seasonal_zh+="\n"
        tag_en=name_en.replace(" ","").replace("'","").replace("/","") if name_en else ""
        tag_zh=name_zh.replace("／","") if name_zh else ""
        if tag_en:
            seasonal_tags+=f" #{tag_en}"
        if tag_zh:
            seasonal_tags+=f" #{tag_zh}"
        if event_type=="solar_term":
            seasonal_tags+=" #二十四節氣"

    if is_evening:
        main_temp=w.get("temperature",w["high"])
        caption=f"""Hi, I’m Taipei Cat! 🐱
The city lights are coming on — here’s your little weather note for tonight.

{date} Taipei Evening Weather 🌙 📍 Taipei Meowcast

🌙 Tonight’s Weather
📍 Taipei, Taiwan
🌡️ Around 17:00: {main_temp}°C / Tonight’s low {w['low']}°C
🌧️ Highest rain chance this evening: {rain}%
This evening is {en_condition}.

🐾 Taipei Cat’s evening note
As Taipei slows down for the night, the light changes, the streets cool, and the city finds a different rhythm.
Whether you’re heading home or taking one last walk, I hope your evening feels calm and cozy. 💛

🌙 今晚台北天氣
📍 台北，台灣
🌡️ 17:00 約 {main_temp}°C / 今晚低溫 {w['low']}°C
🌧️ 傍晚至今晚最高降雨機率：{rain}%
今晚{zh_condition}。

🐱 台北貓的晚安提醒
天色慢慢暗下來，台北也換上了晚上的節奏。
不管你正在回家，還是準備出去走走，都希望今晚的你舒服、平安，也有一點屬於自己的悠閒。 🌙

Have a lovely evening in Taipei. 💛
祝你在台北有個舒服的夜晚。

#TaipeiCat #TaipeiMeowcast #TaipeiWeather #TaipeiEvening #WeatherCat #Taipei101 #Taipei #Taiwan #台北天氣 #台北夜晚"""
        return t,caption

    caption=f"""Hi, I’m Taipei Cat! 🐱
Exploring Taipei with you, one little adventure and one weather forecast at a time.

{seasonal_en}{date} Taipei Weather 📍 Taipei Meowcast

🌤️ Today’s Weather
📍 Taipei, Taiwan
🌡️ High {w['high']}°C / Low {w['low']}°C
🌧️ Rain chance: {rain}%
Today is {en_condition}.

🐾 Taipei Cat’s little note
Weather changes the city in tiny ways — the light, the breeze, the pace of a walk, even where a cat chooses to sit.
Whatever the sky looks like today, I hope you find one small corner of Taipei that feels good to you. 💛

{seasonal_zh}🌤️ 今日台北天氣
📍 台北，台灣
🌡️ 最高 {w['high']}°C / 最低 {w['low']}°C
🌧️ 降雨機率：{rain}%
今天{zh_condition}。

🐱 台北貓的小提醒
天氣不只是溫度和降雨機率，也悄悄改變一座城市的光線、風、散步的速度。
不管今天是晴是雨，都希望你在台北找到一個讓自己舒服的小角落。

Have a lovely day in Taipei. 💛
祝你在台北度過美好的一天。

#TaipeiCat #TaipeiMeowcast #TaipeiWeather #WeatherCat #Taipei101 #Taipei #Taiwan #台北天氣 #台北生活{seasonal_tags}"""
    return t,caption


def make_simple_caption(w,event=None,city=None):
    city=city or load_city_config()
    if city.get("language")=="bilingual" and city.get("id")=="taipei":
        return _simple_taipei_caption(w,city,event=event)
    return _simple_english_caption(w,city,event=event)


def _extract_response_text(data):
    parts=[]
    for item in data.get("output",[]):
        for content in item.get("content",[]):
            if content.get("type")=="output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def make_ai_caption(w,simple_caption,config,city=None):
    city=city or load_city_config()
    api_key=os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    language_instruction=(
        "Use English + Traditional Chinese."
        if city.get("language")=="bilingual"
        else "Use English only."
    )
    prompt=f"""You write captions for {city.get('brand')}, a gentle cat-weather account.
Rewrite the factual caption below into a warm, playful caption. {language_instruction}
Keep every weather number exactly unchanged. Do not invent weather facts.
Preserve the time-of-day framing. Keep it concise enough for Instagram/Facebook.
Keep the {city.get('cat_name')} voice cute but not childish. End with relevant hashtags.

FACTUAL CAPTION:
{simple_caption}"""
    response=requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
        json={"model":config.get("aiModel","gpt-5.6-luna"),"input":prompt},
        timeout=60,
    )
    response.raise_for_status()
    text=_extract_response_text(response.json())
    if not text:
        raise RuntimeError("AI returned an empty caption")
    return text


def make_caption(w,event=None,city=None):
    city=city or load_city_config()
    config=load_config()
    t,simple_caption=make_simple_caption(w,event=event,city=city)
    if not config.get("isAI",False):
        print("Caption mode: SIMPLE (isAI=false)")
        return t,simple_caption
    try:
        ai_caption=make_ai_caption(w,simple_caption,config,city=city)
        print("Caption mode: AI")
        return t,ai_caption
    except Exception as exc:
        print(f"AI caption failed; using SIMPLE fallback: {exc}")
        return t,simple_caption
