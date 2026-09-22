def theme(w):
    if w["rain"] >= 50 or w["code"] >= 51: return "rainy"
    if w["high"] >= 32: return "hot"
    if w["high"] <= 18: return "cold"
    if w["code"] in (0,1): return "sunny"
    return "cloudy"

LINES={
"sunny":("Sunshine is on duty.","陽光值班中，出門走走吧！"),
"rainy":("Rainy day. Paws stay dry.","今天記得帶傘，貓也不想淋濕。"),
"cloudy":("Cloudy skies. Cozy vibes.","有點陰天，但心情依然柔軟。"),
"hot":("Stay cool. More treats!","天氣好熱，記得多喝水！"),
"cold":("Cold days. Warm hearts.","天氣有點冷，記得保暖喔！")}

def make_caption(w):
    t=theme(w); en,zh=LINES[t]
    return t, f"Taipei Meowcast 🐾\n{w['date']} · {w['low']}–{w['high']}°C · Rain {w['rain']}%\n\n{en}\n{zh}\n\n#TaipeiMeowcast #TaipeiWeather #台北天氣 #CatReels"
