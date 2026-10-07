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
    """Choose artwork from the actual forecast condition code.

    Rain probability stays informational and must not force rainy artwork.
    WMO 0-1 = clear/mainly clear, 2-3/45/48 = cloudy/fog,
    and precipitation codes 51+ use rainy artwork.
    """
    code=int(w["code"])
    if code >= 51:
        return "rainy"
    if code in (0, 1):
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


HUMOR_LINES = {
    "taipei": {
        "morning": {
            "sunny": [
                [
                    "太陽今天有打卡。我也有，只是打完就想躺回去。",
                    "The sun clocked in. So did I. My next meeting is with a cushion."
                ],
                [
                    "今日行程：你忙你的，我負責把窗邊那格陽光躺滿。",
                    "You handle your schedule. I'll handle occupying the entire sunny patch."
                ],
                [
                    "陽光到貨，貓肚準備簽收。你出門記得防曬，別跟我比誰比較會曬。",
                    "Sunshine delivery! My belly is ready to sign for it. Sunscreen for you, a window seat for me."
                ]
            ],
            "cloudy": [
                [
                    "雲很多，待辦也很多。建議先喝口水，別急著跟天空一起皺眉。",
                    "Plenty of clouds, plenty of tasks. Have some water before joining the sky in looking serious."
                ],
                [
                    "天空開了柔焦，我的起床速度也順便調成慢動作。",
                    "The sky has switched to soft focus. I've switched to slow-motion mornings."
                ],
                [
                    "太陽暫時躲起來。別催，我躲棉被時也不喜歡被催。",
                    "The sun is keeping a low profile. As a duvet enthusiast, I respect that."
                ]
            ],
            "rainy": [
                [
                    "雨天出門三件事：帶傘、看路、別踩水坑。第三件主要是我本人很介意。",
                    "Rainy-day checklist: umbrella, careful steps, no puddles. My paws are very particular about that last one."
                ],
                [
                    "傘是你的隨身屋頂。我有毛，但這不代表我想試用淋浴功能。",
                    "Your umbrella is a portable roof. I have fur, but that doesn't mean I ordered a shower."
                ],
                [
                    "今天鞋子不想游泳，貓掌也不想。帶把傘，我在乾的地方精神支持你。",
                    "Your shoes didn't sign up for swimming. Neither did my paws. Bring an umbrella; I'll cheer from somewhere dry."
                ]
            ]
        },
        "evening": {
            "sunny": [
                [
                    "晚間預報偏晴，適合把步調放慢。我的步調已經慢到沙發認不出我有移動。",
                    "A clear evening calls for a slower pace. Mine is so slow the sofa hasn't detected movement."
                ],
                [
                    "今天辛苦了，晚間天空偏晴。你可以收工，我還有一場很重要的晚飯要出席。",
                    "You've earned a break under this clear evening sky. I still have a very important dinner appointment."
                ],
                [
                    "今晚偏晴，回家路上慢慢走。我的散步路線是飯碗到沙發，導航不用開。",
                    "A clear evening for taking your time on the way home. My route is bowl to sofa. No navigation required."
                ]
            ],
            "cloudy": [
                [
                    "今晚天空蓋雲被。你也可以找條毯子，但先確認下面沒有一隻已經下班的貓。",
                    "The sky has a cloud blanket tonight. Get yourself a real one, after checking for an off-duty cat underneath."
                ],
                [
                    "雲還在值班，我準備交班給沙發。你也別把所有待辦帶進被窩。",
                    "The clouds are still on duty. I'm handing over to the sofa. Try leaving your to-do list outside the duvet."
                ],
                [
                    "晚間多雲，天空今晚走低調路線。我也低調，只是在飯碗空了的時候例外。",
                    "A cloudy evening: the sky is keeping things low-key. So am I, unless the food bowl is empty."
                ]
            ],
            "rainy": [
                [
                    "今晚有雨，回家記得帶傘。至於我，已經把沙發列為防水避難所。",
                    "Rain this evening: take an umbrella home. I've designated the sofa as my dry retreat."
                ],
                [
                    "雨天回家先擦乾，再躺平。別問順序，沙發跟我都很在意。",
                    "Home in the rain? Dry off, then flop. The sofa and I are very invested in that order."
                ],
                [
                    "今晚的雨聲留給窗外，疲累留在門口。雨傘也留門口，別甩到我。",
                    "Leave the rain outside and your workday at the door. The wet umbrella too, preferably away from me."
                ]
            ]
        }
    },
    "melbourne": {
        "morning": {
            "sunny": [
                [
                    "Window-seat weather. I have no ticket, but I do have excellent squatters' rights.",
                    ""
                ],
                [
                    "Sunshine on the forecast, absolutely no ambition on the cat. A balanced start.",
                    ""
                ],
                [
                    "Your morning commute has stops. Mine has one: the sunny patch by the window.",
                    ""
                ]
            ],
            "cloudy": [
                [
                    "The sky is wearing grey. Very Melbourne. I've dressed for the occasion in my usual fur.",
                    ""
                ],
                [
                    "Clouds overhead, coffee on your mind, breakfast on mine. We all have priorities.",
                    ""
                ],
                [
                    "The sun is working behind the scenes. I'm working from the cushions. Flexible arrangements all round.",
                    ""
                ]
            ],
            "rainy": [
                [
                    "Take a brolly. Your shoes aren't boats, and my paws have a strict no-puddles policy.",
                    ""
                ],
                [
                    "Rain on the forecast. My outdoor ambitions have been redirected to an indoor nap.",
                    ""
                ],
                [
                    "Melbourne has booked a rinse cycle. Bring a brolly; your outfit didn't volunteer.",
                    ""
                ]
            ]
        },
        "evening": {
            "sunny": [
                [
                    "A clear evening and a full calendar: dinner, sofa, stare at nothing. Fully booked.",
                    ""
                ],
                [
                    "Clear skies tonight. Take the scenic route home; I'll take the extremely scenic route to my bowl.",
                    ""
                ],
                [
                    "You can clock off. Under this clear evening sky, my night shift starts with dinner and ends with more dinner negotiations.",
                    ""
                ]
            ],
            "cloudy": [
                [
                    "The sky's got a cloud blanket. I'll take the one on your sofa. Ownership is a flexible concept.",
                    ""
                ],
                [
                    "Cloudy tonight. Excellent atmosphere for doing very little with tremendous confidence.",
                    ""
                ],
                [
                    "The clouds are staying late. You don't have to. Your sofa and its resident cat await.",
                    ""
                ]
            ],
            "rainy": [
                [
                    "Rain tonight. Bring a brolly, dry your shoes, and please don't shake the umbrella near management. I'm management.",
                    ""
                ],
                [
                    "Tonight's rain gets the window seat. I get the dry seat. A fair arrangement.",
                    ""
                ],
                [
                    "A wet evening outside, a very serious nap inside. Bring a brolly; I'll handle sofa security.",
                    ""
                ]
            ]
        }
    }
}

WEEKDAY_LINES = {
    "taipei": {
        "morning": [
            ["太陽今天有打卡，我也有，只是打完就想躺回去。週一先求生存，不求完美。", "The sun clocked in. So did I. Monday is for survival, not perfection."],
            ["週二沒有週一那麼可怕，但離週五也沒有你想像中那麼近。", "Tuesday is less scary than Monday, but Friday is not as close as you think."],
            ["撐過今天就過一半了。連本貓都已經連續上班三天。", "Halfway day. Even this cat has clocked in three days in a row."],
            ["週末已經出現在雷達邊緣。衣服穿對、雨傘帶對，剩下的人生問題本貓不負責。", "The weekend is on the radar. Dress right, pack smart; the rest is above my pay grade."],
            ["星期五到了。本貓今天播天氣的速度都比較快，靈魂已經先進入週末模式。", "Friday has arrived. Even this forecast feels faster; my soul is already on weekend mode."],
            ["今天唯一合理的早起理由：早餐、旅行，或被貓踩醒。睡到自然醒也是一種安排。", "Valid reasons to wake early on Saturday: breakfast, travel, or a cat. Sleeping in is also a plan."],
            ["今天請慢慢來。因為明天的事情，本貓決定明天再想。", "Take Sunday slowly. Tomorrow's problems have been officially postponed until tomorrow."]
        ],
        "evening": [
            ["恭喜，今天最困難的任務已完成：活過星期一。回家、吃飯、洗澡、躺平。", "Monday survived. Go home, eat, shower, flop. Tomorrow belongs to tomorrow's cat."],
            ["本貓已完成今日第二次氣象勤務，現在準備進入沙發值勤模式。你也可以下班了。", "Second weather shift complete. I'm transferring to sofa duty. You may clock off too."],
            ["這個星期已經走完一半。如果你現在很累，非常合理。剩下的一半明天再處理。", "Half the week is done. If you're tired, that's reasonable. The other half can wait until tomorrow."],
            ["本貓精密計算：再睡一次，醒來就是星期五。請保存體力。", "Precise cat maths: one more sleep and it's Friday. Conserve your energy."],
            ["星期五晚間模式啟動。工作訊息：不接受。週末正式開始。", "Friday night mode: on. Work messages: declined. The weekend is officially open."],
            ["沒有鬧鐘，沒有 Monday meeting，沒有理由太早睡。這就是本貓理解的自由。", "No alarm, no Monday meeting, no reason to rush. This is my definition of freedom."],
            ["如果你突然想起明天是星期一，請不要驚慌。先睡好，明早本貓會先去上班。", "If you suddenly remember tomorrow is Monday, don't panic. Sleep first; I'll clock in before you."]
        ]
    },
    "melbourne": {
        "morning": [
            ["Monday loading: coffee first, weather second, existential questions after lunch.", ""],
            ["Good news: it's not Monday. Bad news: it's somehow only Tuesday.", ""],
            ["Happy halfway day. We've made it through half the week; even this cat is impressed.", ""],
            ["Thursday detected. Weekend proximity: increasing. Motivation: questionable. Dress in layers—because Melbourne.", ""],
            ["Friday has arrived. Today's forecast includes a strong chance of mentally checking out after 3 PM.", ""],
            ["Saturday priorities: coffee, brunch, perhaps another coffee. Take your time.", ""],
            ["Sunday schedule: do less, eat something nice, pretend Monday doesn't exist. Excellent plan.", ""]
        ],
        "evening": [
            ["Monday survived. Go home, eat something, become horizontal. You've earned it.", ""],
            ["Tuesday weather shift complete: humans informed, couch calling. Good night, Melbourne.", ""],
            ["Wednesday done. Three days survived, two workdays remaining. Cat mathematics never lies.", ""],
            ["Important Thursday announcement: when you wake up, it's Friday. Rest accordingly.", ""],
            ["Friday night: work emails absolutely not. This cat now accepts payment exclusively in snacks.", ""],
            ["Saturday night: stay out late, stay home early, order dessert. There are no wrong answers.", ""],
            ["Yes, tomorrow is Monday. No, we don't need to discuss it yet. I'll clock in again at 7 AM.", ""]
        ]
    }
}

def _voice_lines(w, city):
    """Choose deterministic copy by each city's local forecast date weekday."""
    from datetime import date
    period = "evening" if w.get("period") == "evening" else "morning"
    custom_lines = city.get("weekday_lines")
    voice = city["id"] if custom_lines else ("taipei" if city.get("id") == "taipei" else "melbourne")
    local_date = date.fromisoformat(w["date"])
    weekday = local_date.weekday()  # Monday=0 ... Sunday=6
    templates = custom_lines if custom_lines else WEEKDAY_LINES[voice]
    first, second = templates[period][weekday]
    weekday_name = local_date.strftime("%A")
    template_id = f"{voice}-{period}-{weekday_name.lower()}"
    print(f"Caption template: {voice} / {w['date']} / {weekday_name} / {period} / template={template_id}")
    en, zh = (second, first) if voice == "taipei" else (first, "")
    # Keep useful weather-dependent reminders on top of the weekday personality.
    temp = w.get("temperature", w["high"]) if period == "evening" else w["high"]
    if temp >= 32:
        en += " Drink water and take breaks in the shade. Being fluffy is not a cooling strategy."
        zh += " 記得補水、找陰涼處休息。毛茸茸不是散熱設備。"
    elif temp <= 18:
        en += " Bring a layer. Sadly, my fur coat is not available to borrow."
        zh += " 出門加件衣服。我的毛外套恕不外借。"
    if w["rain"] >= 50 and theme(w) != "rainy":
        en += " The rain chance still calls for an umbrella in your bag. The sky has options."
        zh += " 降雨機率仍偏高，包包放把傘。天空也有備案。"
    return en, zh

def _seasonal_copy(event):
    if not event:
        return "", "", ""
    en_name = event.get("name_en", "")
    zh_name = event.get("name_zh", "")
    en_note = event.get("caption_en") or event.get("note_en", "")
    zh_note = event.get("caption_zh", "")
    en = f"🐾 {en_name}\n{en_note}\n\n" if en_name else ""
    zh = f"🐱 {zh_name}\n{zh_note}\n\n" if zh_name else ""
    tags = []
    for name in (en_name, zh_name):
        safe = "".join(ch for ch in name if ch.isalnum() or ch == "_")
        if safe:
            tags.append("#" + safe)
    if event.get("type") == "solar_term":
        tags.append("#二十四節氣")
    return en, zh, (" " + " ".join(tags)) if tags else ""


ENGAGEMENT_ZH = "喜歡這隻愛碎念的天氣貓，就幫我點個愛心 ❤️、追蹤台北天氣貓！每天早晚一起看天氣，出門帶傘還是帶墨鏡，先問貓再出門。🐾"
ENGAGEMENT_EN = "Enjoy your daily pawcast? Tap the heart ❤️ and follow for weather with a side of cat attitude, every morning and evening. Forecast first, nap later. 🐾"


def _simple_english_caption(w, city, event=None):
    t = theme(w)
    en_condition, _ = LINES[t]
    date = w["date"].replace("-", "/")
    name = city["display_name"]
    cat = city["cat_name"]
    brand = city.get("brand", f"{name} Meowcast")
    country = city.get("country", "")
    evening = w.get("period") == "evening"
    note, _ = _voice_lines(w, city)
    seasonal, _, extra_tags = _seasonal_copy(event)
    if evening:
        title = f"{date} {brand} | Evening pawcast 🌙"
        weather = (
            f"🌡️ Around 17:00: {w.get('temperature', w['high'])}°C / Tonight’s low {w['low']}°C\n"
            f"🌧️ Highest rain chance this evening: {w['rain']}%\n"
            f"Evening forecast: {en_condition}."
        )
        hello = f"{cat} reporting for the evening shift. Dinner negotiations are next. 🐱"
        closing = "Clock off when you can. The sofa won't sit on itself. 🐾"
        extra_tags += f" #{name}Evening"
    else:
        title = f"{date} {brand} | Morning pawcast ☀️"
        weather = (
            f"🌡️ High {w['high']}°C / Low {w['low']}°C\n"
            f"🌧️ Rain chance: {w['rain']}%\n"
            f"Morning forecast: {en_condition}."
        )
        hello = f"{cat} here. Forecast first, highly important nap second. 🐱"
        closing = "Go easy on yourself. Even cats take a break from taking breaks. 🐾"
    return t, f"{hello}\n\n{title}\n📍 {name}, {country}\n{weather}\n\n{seasonal}🐾 The cat’s verdict\n{note}\n\n{closing}\n\n{ENGAGEMENT_EN}\n\n{_tags(city, extra_tags)}"


def _simple_taipei_caption(w, city, event=None):
    t = theme(w)
    en_condition, zh_condition = LINES[t]
    date = w["date"].replace("-", "/")
    evening = w.get("period") == "evening"
    en_note, zh_note = _voice_lines(w, city)
    seasonal_en, seasonal_zh, extra_tags = _seasonal_copy(event)
    if evening:
        title = f"{date} 台北天氣貓｜晚班喵報 | Taipei Meowcast 🌙"
        temp = w.get("temperature", w["high"])
        weather_zh = (
            f"🌡️ 17:00 約 {temp}°C / 今晚低溫 {w['low']}°C\n"
            f"🌧️ 傍晚至今晚最高降雨機率：{w['rain']}%\n"
            f"晚間預報：{zh_condition}。"
        )
        weather_en = (
            f"🌡️ Around 17:00: {temp}°C / Tonight’s low {w['low']}°C\n"
            f"🌧️ Highest rain chance this evening: {w['rain']}%\n"
            f"Evening forecast: {en_condition}."
        )
        hello_zh = "台北貓晚班打卡！先報天氣，再跟飯碗開會。🐱"
        hello_en = "Taipei Cat, evening shift. Forecast first, dinner meeting next. 🐱"
        close_zh = "今天辛苦了。能收工就收工，沙發不會自己坐。🐾"
        close_en = "You've done enough for today. The sofa won't sit on itself. 🐾"
        extra_tags += " #TaipeiEvening #台北夜晚"
    else:
        title = f"{date} 台北天氣貓｜早班喵報 | Taipei Meowcast ☀️"
        weather_zh = (
            f"🌡️ 最高 {w['high']}°C / 最低 {w['low']}°C\n"
            f"🌧️ 降雨機率：{w['rain']}%\n"
            f"早間預報：{zh_condition}。"
        )
        weather_en = (
            f"🌡️ High {w['high']}°C / Low {w['low']}°C\n"
            f"🌧️ Rain chance: {w['rain']}%\n"
            f"Morning forecast: {en_condition}."
        )
        hello_zh = "台北貓早班打卡！眼睛睜開了，靈魂還在棉被裡。🐱"
        hello_en = "Taipei Cat clocking in. Eyes open, soul still under the duvet. 🐱"
        close_zh = "今天照自己的步調走。貓都會休息，你也可以。🐾"
        close_en = "Take today at your own pace. Even cats take breaks from taking breaks. 🐾"
    return t, (
        f"{hello_zh}\n\n{title}\n📍 台北，台灣\n{weather_zh}\n\n"
        f"{seasonal_zh}🐱 台北貓的碎念\n{zh_note}\n\n{close_zh}\n\n{ENGAGEMENT_ZH}\n\n"
        f"— English pawcast —\n{hello_en}\n📍 Taipei, Taiwan\n{weather_en}\n\n"
        f"{seasonal_en}🐾 The cat’s verdict\n{en_note}\n\n{close_en}\n\n{ENGAGEMENT_EN}\n\n"
        f"{_tags(city, extra_tags)}"
    )


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
        "Use Traditional Chinese first, then English. All Chinese content, including the like-and-follow reminder, must precede the English section."
        if city.get("language")=="bilingual"
        else "Use English only."
    )
    prompt=f"""You write captions for {city.get('brand')}, a witty cat-weather account.
Rewrite the caption below with concise, observational cat humour: one strong joke and a useful weather reminder. {language_instruction}
Keep every weather number exactly unchanged. Do not invent weather facts.
Preserve the time-of-day framing. Keep it concise enough for Instagram/Facebook.
Taipei voice: Traditional Chinese first, then natural English; an affectionate, mildly grumbling neighbourhood cat. Use Taiwanese everyday phrasing, not forced slang.
Melbourne voice: natural Australian English, dry wit, brollies, commutes and sofa ownership; no caricature or forced puns.
Make the cat the butt of the joke. Keep morning and evening distinct. Avoid repetitive motivational platitudes.
Never invent current rain, wind, humidity, UV, transport disruption, or a guaranteed dry period from probabilities.
Keep the date (including year), city, brand, temperatures, rain chance and its time window. No invented percentages.
Preserve any named calendar event and its meaning. Treat remembrance days and Qingming respectfully, without jokes.
Keep the {city.get('cat_name')} voice warm, witty and not childish.
Every caption must ask readers to tap the heart, follow the account, and return for weather every morning and evening. Preserve the engagement reminder from the factual caption verbatim in each language. Place reminders before relevant hashtags.
For Taipei, put Chinese before English in titles and every paired label as well as the full language sections. End with relevant hashtags.

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
    if "isAI" in city:
        config={**config,"isAI":city["isAI"]}
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
