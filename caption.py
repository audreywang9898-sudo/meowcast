def theme(w):
    if w["rain"] >= 50 or w["code"] >= 51: return "rainy"
    if w["high"] >= 32: return "hot"
    if w["high"] <= 18: return "cold"
    if w["code"] in (0,1): return "sunny"
    return "cloudy"

LINES={
"sunny":("hot and sunny","Sunshine is on duty. ☀️","Early walks, blue skies and a little iced coffee."),
"rainy":("rainy with showers around","Rainy paws on duty. 🌧️","Umbrella nearby, slower steps and cozy café time."),
"cloudy":("cloudy and comfortable","Cloudy, but cozy. ☁️","A softer Taipei day for wandering and taking it easy."),
"hot":("hot with sunny intervals","Stay cool out there. ☀️🥤","Shade, water and iced drinks are Taipei Cat's survival kit."),
"cold":("cool and chilly","Cold day, warm heart. 🧣","Layers on, warm drink ready, paws staying cozy.")}

def make_caption(w):
    t=theme(w)
    condition,opening,activity=LINES[t]
    rain=w["rain"]
    date=w["date"].replace("-","/")

    if rain >= 60:
        umbrella="☂️ Keep an umbrella nearby!"
    elif rain >= 30:
        umbrella="🌦️ A passing shower is possible, so a small umbrella may help."
    else:
        umbrella="🐾 Rain chance is low — enjoy the city."

    if t=="hot":
        reminder="Taipei is bringing the heat today. Drink some water, find a little shade, and don't rush."
        reflection="Even on the hottest days, a small patch of shade can make everything feel gentler."
    elif t=="rainy":
        reminder="Rain changes the rhythm of Taipei. Walk a little slower and let the city sparkle."
        reflection="You don't need every day to be perfectly sunny to have a beautiful life."
    elif t=="cold":
        reminder="A cooler Taipei day calls for warm layers, warm drinks and warm thoughts."
        reflection="Some days are made for moving slowly and keeping the good things close."
    elif t=="cloudy":
        reminder="Not every beautiful day needs a blue sky. Taipei Cat approves of cozy clouds too."
        reflection="Soft skies can still hold a very good day."
    else:
        reminder="Good weather, good mood — Taipei Cat is officially on sunshine duty."
        reflection="Sunshine doesn't have to make life perfect. Sometimes it just reminds us to enjoy the view."

    return t, f"""Hi, I’m Taipei Cat! 🐱
Exploring Taipei with you, one little adventure and one weather forecast at a time.

{date} Taipei Weather 📍 Taipei Meowcast

{opening}

Today is {condition}, around {w['high']}°C in the daytime. Taipei Cat is checking the sky, enjoying the city and deciding where the next snack should happen. 😹

🌤️ Today’s Weather
📍 Taipei, Taiwan
🌡️ {w['high']}°C / {w['low']}°C
🌧️ Rain chance: {rain}%
{umbrella}

😸 Today’s Happiness Index 😸😸😸😸☆

Perfect for:
🐾 {activity}
📸 A little Taipei photography
☕ Taking a break when you need one
🌇 Enjoying the city at your own pace

🐟 Daily Tuna Index 🐟🐟🐟🐟🐟

Taipei Cat: looking majestic. 😼
Also Taipei Cat: wondering where lunch is. 😹

🐾 Taipei Cat’s Little Reminder

{reminder}

{reflection}

Take care of yourself, keep going gently, and enjoy the view along the way. 🐱🐾

If you love cute cats + weather vibes + cozy Taipei content, please like & follow ❤️
Taipei Cat Weather Forecast is here! 🐾

Every ❤️ is another can of tuna keeping this weather cat on duty. 🐟

#TaipeiCat #TaipeiMeowcast #TaipeiWeather #WeatherCat #Taipei101 #Taipei #Taiwan"""
