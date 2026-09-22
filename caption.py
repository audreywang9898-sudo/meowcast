import json
import os
import requests

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
    if w["rain"] >= 50 or w["code"] >= 51:
        return "rainy"
    if w["high"] >= 32:
        return "hot"
    if w["high"] <= 18:
        return "cold"
    if w["code"] in (0, 1):
        return "sunny"
    return "cloudy"


LINES = {
    "sunny": ("sunny", "晴朗"),
    "rainy": ("rainy with showers", "有雨，可能有陣雨"),
    "cloudy": ("cloudy", "多雲"),
    "hot": ("hot with sunny intervals", "炎熱，間有陽光"),
    "cold": ("cool and chilly", "涼冷"),
}


def make_simple_caption(w):
    t = theme(w)
    en_condition, zh_condition = LINES[t]
    date = w["date"].replace("-", "/")
    rain = w["rain"]

    caption = f"""Hi, I’m Taipei Cat! 🐱
Exploring Taipei with you, one little adventure and one weather forecast at a time.

{date} Taipei Weather 📍 Taipei Meowcast

🌤️ Today’s Weather
📍 Taipei, Taiwan
🌡️ {w['high']}°C / {w['low']}°C
🌧️ Rain chance: {rain}%
Today is {en_condition}. 🐾

🌤️ 今日台北天氣
📍 台北，台灣
🌡️ 最高 {w['high']}°C / 最低 {w['low']}°C
🌧️ 降雨機率：{rain}%
今天{zh_condition}。🐱

Have a lovely day in Taipei. 💛
祝你在台北度過美好的一天。

#TaipeiCat #TaipeiMeowcast #TaipeiWeather #Taipei #Taiwan #台北天氣 #台北生活"""
    return t, caption


def _extract_response_text(data):
    # Responses API normally returns text inside output -> content -> output_text.
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def make_ai_caption(w, simple_caption, config):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = f"""You write captions for Taipei Meowcast, a gentle cat-weather account.
Rewrite the factual caption below into a warm, playful bilingual English + Traditional Chinese caption.
Keep every weather number exactly unchanged. Do not invent weather facts.
Keep it concise enough for Instagram/Facebook. Keep the Taipei Cat voice cute but not childish.
End with relevant hashtags.

FACTUAL CAPTION:
{simple_caption}"""

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.get("aiModel", "gpt-5.6-luna"),
            "input": prompt,
        },
        timeout=60,
    )
    response.raise_for_status()
    text = _extract_response_text(response.json())
    if not text:
        raise RuntimeError("AI returned an empty caption")
    return text


def make_caption(w):
    config = load_config()
    t, simple_caption = make_simple_caption(w)

    if not config.get("isAI", False):
        print("Caption mode: SIMPLE (isAI=false)")
        return t, simple_caption

    try:
        ai_caption = make_ai_caption(w, simple_caption, config)
        print("Caption mode: AI")
        return t, ai_caption
    except Exception as exc:
        # AI is optional: publishing must continue even if the API/key/network fails.
        print(f"AI caption failed; using SIMPLE fallback: {exc}")
        return t, simple_caption
