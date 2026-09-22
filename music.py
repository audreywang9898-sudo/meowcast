import math, os, wave, struct
from datetime import datetime
from zoneinfo import ZoneInfo

SR=22050
DUR=8

# Seven everyday tracks. Solar-term days can select one of the 24 original
# procedural themes below instead, so the system remains AI-independent.
TRACKS=[
    (104,[60,64,67,72,67,64,62,67],"Fresh Start"),
    (112,[64,67,69,71,69,67,64,62],"Sunny Steps"),
    (92,[57,60,64,67,64,60,59,64],"Cozy City"),
    (108,[62,66,69,74,69,66,64,69],"Little Adventure"),
    (118,[60,64,67,69,72,69,67,64],"Happy Paws"),
    (84,[55,59,62,67,62,59,57,62],"Slow Morning"),
    (78,[60,64,67,71,67,64,62,60],"Soft Sunshine"),
]

# slug: (Chinese, English, bpm, MIDI melody)
SOLAR_TERMS={
    "lichun":("立春","Beginning of Spring",92,[60,64,67,72,69,67,64,67]),
    "yushui":("雨水","Rain Water",82,[62,65,69,67,65,62,60,65]),
    "jingzhe":("驚蟄","Awakening of Insects",108,[60,67,69,72,67,74,72,69]),
    "chunfen":("春分","Spring Equinox",98,[64,67,71,72,71,67,64,69]),
    "qingming":("清明","Pure Brightness",76,[57,60,64,62,60,57,55,60]),
    "guyu":("穀雨","Grain Rain",86,[60,62,65,69,67,65,62,60]),
    "lixia":("立夏","Beginning of Summer",112,[64,69,71,76,71,69,67,71]),
    "xiaoman":("小滿","Grain Buds",106,[62,66,69,74,71,69,66,64]),
    "mangzhong":("芒種","Grain in Ear",116,[60,64,69,72,76,72,69,67]),
    "xiazhi":("夏至","Summer Solstice",120,[67,71,74,79,76,74,71,72]),
    "xiaoshu":("小暑","Minor Heat",110,[64,67,72,76,74,72,69,67]),
    "dashu":("大暑","Major Heat",118,[62,69,74,78,74,71,69,66]),
    "liqiu":("立秋","Beginning of Autumn",94,[60,64,67,71,69,67,64,62]),
    "chushu":("處暑","End of Heat",88,[62,65,69,72,69,67,65,60]),
    "bailu":("白露","White Dew",80,[67,71,74,71,69,67,64,62]),
    "qiufen":("秋分","Autumn Equinox",84,[60,64,67,71,67,64,62,60]),
    "hanlu":("寒露","Cold Dew",74,[57,60,64,67,64,62,60,55]),
    "shuangjiang":("霜降","Frost's Descent",70,[55,59,62,67,64,62,59,57]),
    "lidong":("立冬","Beginning of Winter",76,[60,63,67,70,67,63,58,60]),
    "xiaoxue":("小雪","Minor Snow",72,[64,67,71,76,71,69,67,64]),
    "daxue":("大雪","Major Snow",68,[57,60,64,69,64,62,60,57]),
    "dongzhi":("冬至","Winter Solstice",66,[60,64,67,72,67,64,59,60]),
    "xiaohan":("小寒","Minor Cold",70,[62,65,69,65,62,60,57,60]),
    "dahan":("大寒","Major Cold",64,[55,60,63,67,63,60,58,55]),
}

def hz(n):
    return 440*2**((n-69)/12)

def _render(path,bpm,notes,title,duration=DUR):
    os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
    n=int(SR*duration)
    audio=[0.0]*n
    beat=60/bpm
    for k in range(int(duration/beat)+1):
        st=k*beat
        f=hz(notes[k%len(notes)])
        for i in range(int(st*SR),min(n,int((st+.5)*SR))):
            t=i/SR-st
            env=(1-math.exp(-12*t))*math.exp(-4.2*t)
            # Soft rounded tone: gentle attack, restrained harmonic content.
            audio[i]+=.13*env*(math.sin(2*math.pi*f*t)+.10*math.sin(4*math.pi*f*t))
    root=hz(notes[0]-12)
    for i in range(n):
        t=i/SR
        audio[i]+=.018*math.sin(2*math.pi*root*t)
    peak=max(map(abs,audio)) or 1
    with wave.open(path,"w") as w:
        w.setparams((1,2,SR,n,"NONE","not compressed"))
        w.writeframes(b"".join(
            struct.pack("<h",int(max(-1,min(1,x/peak*.62))*32767)) for x in audio
        ))
    print("BGM:",title)
    return path

HOLIDAY_TRACKS={
    # Original procedural themes: festive in style, not copies of existing songs.
    (1,1):("New Year Cat",118,[60,64,67,72,76,72,69,67]),
    (2,14):("Valentine Love Cat",72,[60,64,67,71,69,67,64,60]),
    (2,28):("Peaceful Paws",68,[60,64,67,69,67,64,62,60]),
    (4,4):("Children's Day Cat",116,[60,64,67,72,74,72,69,67]),
    (5,1):("May Day Cat",104,[60,64,67,69,72,69,67,64]),
    (9,28):("Teacher Appreciation Cat",88,[60,64,67,71,69,67,64,62]),
    (10,10):("Taiwan Celebration Cat",112,[60,67,72,76,72,69,67,64]),
    (10,25):("Autumn Taiwan Cat",90,[57,60,64,67,69,67,64,60]),
    (10,31):("Halloween Cat",96,[57,60,63,66,63,60,58,57]),
    (12,24):("Christmas Eve Cat",92,[67,71,74,79,74,71,69,67]),
    (12,25):("Christmas Cat",96,[60,64,67,72,76,72,67,69]),
    (12,31):("New Year's Eve Cat",120,[62,66,69,74,78,74,71,69]),
}

# Taiwan lunar-calendar holidays need year-specific Gregorian dates.
# Keep this table explicit so scheduled posts are deterministic.
LUNAR_HOLIDAYS={
    2026:{
        (2,17):("Lunar New Year Cat",104,[60,64,67,72,76,72,69,67]),
        (3,3):("Lantern Festival Cat",96,[64,67,72,76,72,69,67,64]),
        (6,19):("Dragon Boat Cat",112,[62,67,69,74,71,69,67,62]),
        (8,19):("Qixi Love Cat",74,[60,64,69,72,69,67,64,60]),
        (9,25):("Mid-Autumn Moon Cat",82,[57,60,64,69,67,64,60,57]),
    },
    2027:{
        (2,6):("Lunar New Year Cat",104,[60,64,67,72,76,72,69,67]),
        (2,20):("Lantern Festival Cat",96,[64,67,72,76,72,69,67,64]),
        (6,9):("Dragon Boat Cat",112,[62,67,69,74,71,69,67,62]),
        (8,8):("Qixi Love Cat",74,[60,64,69,72,69,67,64,60]),
        (9,15):("Mid-Autumn Moon Cat",82,[57,60,64,69,67,64,60,57]),
    },
}

def holiday_for_date(dt=None):
    dt=dt or datetime.now(ZoneInfo("Asia/Taipei"))
    return HOLIDAY_TRACKS.get((dt.month,dt.day)) or LUNAR_HOLIDAYS.get(dt.year,{}).get((dt.month,dt.day))

def make_music(path="output/bgm.wav",solar_term=None,dt=None):
    # Priority: holiday > solar term > everyday track.
    holiday=holiday_for_date(dt)
    if holiday:
        title,bpm,notes=holiday
        return _render(path,bpm,notes,title)
    if solar_term and solar_term in SOLAR_TERMS:
        zh,en,bpm,notes=SOLAR_TERMS[solar_term]
        return _render(path,bpm,notes,f"{zh} / {en}")
    now=dt or datetime.now(ZoneInfo("Asia/Taipei"))
    bpm,notes,title=TRACKS[now.weekday()]
    return _render(path,bpm,notes,title)

def generate_solar_term_library(directory="output/solar_terms"):
    """Generate all 24 reusable, original procedural solar-term WAV files."""
    paths=[]
    for slug,(zh,en,bpm,notes) in SOLAR_TERMS.items():
        paths.append(_render(os.path.join(directory,f"{slug}.wav"),bpm,notes,f"{zh} / {en}"))
    return paths

if __name__=="__main__":
    generate_solar_term_library()
