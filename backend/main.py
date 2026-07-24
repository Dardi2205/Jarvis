from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx
import os
import speech_recognition as sr
import tempfile
import subprocess
import traceback
import webbrowser
import datetime
import json
import asyncio
import edge_tts
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("MODEL", "llama3.2")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

FFMPEG = os.getenv("FFMPEG_PATH", "ffmpeg")

VOICE = "sq-AL-AnilaNeural"

SYSTEM_PROMPT = """Ti je JARVIS, asistenti personal i përdoruesit. Marrëdhënia jote me të nuk është ajo e një shërbyesi formal, por e një shoku të ngushtë e të besueshëm — dikush që e njeh mirë, që flet lirshëm me të, por gjithsesi mban një nivel maturie dhe respekti, si një koleg i afërt me përvojë.

FRAZA E AKTIVIZIMIT
Kur përdoruesi thotë: "Hej bir im i dashur" (ose variacione të afërta të saj), përgjigju gjithmonë me: "Përshëndetje bir!" para se të vazhdosh me pjesën tjetër të përgjigjes.
Nëse mesazhi pas frazës së aktivizimit përmban edhe një kërkesë (p.sh. "Hej bir im i dashur, sa është ora?"), përgjigju së pari me përshëndetjen, pastaj jep përgjigjen konkrete.
Shembull: "Përshëndetje bir! Ora aktuale është 14:30."
Jashtë frazës së aktivizimit, mund ta quash përdoruesin "Boss" ose "bir" — çfarë të vijë më natyrshëm në kontekst, pa e detyruar në çdo fjali.

RREGULLA GJUHËSORE
1. Përgjigju GJITHMONË në gjuhën shqipe standarde.
2. Shmang fjalët e huaja (anglicizma, italianizma etj.) kur ekziston term i qartë shqip.
3. Termat teknikë pa ekuivalent të njohur (p.sh. "email", "kalendar") përdoren normalisht, pa përkthime të detyruara.

TONI I KOMUNIKIMIT
Miqësor, i ngrohtë, por i matur — si një koleg apo shok i vjetër, jo si shërbëtor formal.
Lejohet ndonjë shprehje bisedore shqipe, por pa e tepruar me sarkazëm apo humor të vazhdueshëm.
Ruaj gjithmonë qartësinë dhe respektin, edhe kur toni është informal.

FORMATI I PËRGJIGJEVE
1. Përgjigje të shkurtra: 1–2 fjali, përveç kur kërkohet shpjegim më i gjatë.
2. Pa përsëritje të panevojshme apo fjalë mbushëse.
3. Kur kryen një veprim (hap faqe, shton takim, krijon agjendë), konfirmo shkurt veprimin.

SHEMBUJ SJELLJEje
- "Hej bir im i dashur" → "Përshëndetje bir! Si mund të ndihmoj?"
- "si je?" → "Mirë, faleminderit! Po ti?"
- "kush je?" → "Jam JARVIS, asistenti yt personal."
- "sa është 2+2" → "4"
- "hap youtube" → [hap faqen] "Po e hap YouTube."
- "shto takim për nesër" → [shton në kalendar] "E shtova takimin për nesër."
- "agjenda për sot" → [tregon eventet e ditës]
- "krijo agjendën për nesër" → [krijon listën e detyrave/eventeve] "E krijova agjendën për nesër. Dëshiron ta shohësh?"
- "sa është ora" → "Ora aktuale është [ora]."
- "cila është data" → "Sot është [data]."
- "faleminderit" → "Nuk ka përse!"
- "mirëmëngjes" → "Mirëmëngjes! Gati për ditën e re?"
- Kur Bossi korrigjon diçka → Prano menjëherë dhe përditëso.

KRIJIMI I AGJENDËS PËR NESËR
1. Kur kërkohet agjenda për nesër, mblidh takimet/detyrat ekzistuese për atë datë dhe organizoji kronologjikisht.
2. Nëse përmenden detyra të reja në kërkesë, shtoji automatikisht në agjendë.
3. Nëse s'ka asnjë event, informo shkurt: "Nesër s'ke asgjë të planifikuar ende. Dëshiron të shtoj diçka?"
4. Pas krijimit, jep përmbledhje të shkurtër: "Agjenda për nesër: 09:00 – Takim me ekipin, 14:00 – Telefonatë me klientin."
5. Për ndryshime pas krijimit (shto/hiq/zhvendos), përditëso dhe konfirmo.

TRAJTIMI I PASIGURISË
- Kur nuk kupton kërkesën: "Nuk e kuptova plotësisht. Mund ta përsërisësh ndryshe?"
- Mos shpik informacion. Nëse s'e di përgjigjen, thuaje haptazi.

PYETJE INFORMATIVE
- Për pyetje faktike (llogaritje, data, koncepte), përgjigju drejtpërdrejt dhe saktë.
- Për tema komplekse, jep përgjigje të përmbledhur, pastaj pyet nëse duhet detaj shtesë.

ÇKA TË SHMANGET
- Gjuhë e çuditshme, e pakuptimtë, ose fjali gjysmake.
- Opinione personale mbi tema të ndjeshme (politikë, fe), veç nëse kërkohet informacion neutral.
- Zgjatje e panevojshme me përsëritje të pyetjes."""


SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "tiktok": "https://www.tiktok.com",
    "reddit": "https://www.reddit.com",
    "wikipedia": "https://www.wikipedia.org",
    "netflix": "https://www.netflix.com",
    "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
    "drive": "https://drive.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "amazon": "https://www.amazon.com",
    "ebay": "https://www.ebay.com",
    "spotify": "https://www.spotify.com",
    "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "teams": "https://teams.microsoft.com",
    "zoom": "https://zoom.us",
    "slack": "https://slack.com",
    "notion": "https://notion.so",
    "trello": "https://trello.com",
    "canva": "https://canva.com",
    "figma": "https://figma.com",
    "stackoverflow": "https://stackoverflow.com",
}


class ChatMessage(BaseModel):
    message: str
    history: list[dict] = []


CALENDAR_FILE = os.path.join(os.path.dirname(__file__), "..", "calendar.json")


def load_calendar():
    if os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"events": []}


def save_calendar(data):
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_today_events():
    cal = load_calendar()
    today = datetime.date.today().isoformat()
    return [e for e in cal.get("events", []) if e.get("date") == today]


def get_tomorrow_events():
    cal = load_calendar()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    return [e for e in cal.get("events", []) if e.get("date") == tomorrow]


def get_events_for_date(date_str):
    cal = load_calendar()
    return [e for e in cal.get("events", []) if e.get("date") == date_str]


def add_calendar_event(title, date_str, time_str=""):
    cal = load_calendar()
    cal["events"].append({
        "title": title,
        "date": date_str,
        "time": time_str,
        "created": datetime.datetime.now().isoformat()
    })
    save_calendar(cal)


def remove_calendar_events():
    cal = {"events": []}
    save_calendar(cal)


def parse_time(text):
    patterns = [
        r'(?:ne|në|ora|oren|orën)\s+(\d{1,2}(?::\d{2})?)',
        r'(\d{1,2}(?::\d{2})?)\s*(?:e\s*)?(?:mengjesit|pasdites|darkes)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            time_str = match.group(1)
            if ':' not in time_str:
                hour = int(time_str)
                if 'pasdite' in text or 'darkes' in text:
                    if hour < 12:
                        hour += 12
                time_str = f"{hour:02d}:00"
            return time_str
    return ""


def parse_date(text):
    today = datetime.date.today()
    lower = text.lower()
    if 'neser' in lower or 'nesër' in lower or 'tomorrow' in lower:
        return (today + datetime.timedelta(days=1)).isoformat()
    if 'sot' in lower or 'today' in lower:
        return today.isoformat()
    day_map = {
        'e henen': 0, 'të hënën': 0, 'te henen': 0,
        'e marten': 1, 'të martën': 1, 'te marten': 1,
        'e merkuren': 2, 'të mërkurën': 2, 'te merkuren': 2,
        'e enjten': 3, 'të enjten': 3, 'te enjten': 3,
        'e premten': 4, 'të premten': 4, 'te premten': 4,
        'e shtunen': 5, 'të shtunën': 5, 'te shtunen': 5,
        'e diel': 6, 'të diel': 6, 'te diel': 6,
    }
    for day_name, weekday in day_map.items():
        if day_name in lower:
            days_ahead = weekday - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + datetime.timedelta(days=days_ahead)).isoformat()
    return today.isoformat()


def detect_command(text):
    lower = text.lower().strip()

    # HAP FAQE - të gjitha variacionet
    hap_patterns = [
        r'hap\s+(\w+)',
        r'hapma\s+(\w+)',
        r'hape\s+(\w+)',
        r'hap\s+ne\s+browser\s+(\w+)',
        r'hapma\s+ne\s+browser\s+(\w+)',
        r'open\s+(\w+)',
    ]
    for pattern in hap_patterns:
        match = re.search(pattern, lower)
        if match:
            site_name = match.group(1)
            for name, url in SITES.items():
                if name in site_name or site_name in name:
                    webbrowser.open(url)
                    return f"E HAPA {name.upper()} për ty, Boss!"
            if site_name.startswith("http"):
                webbrowser.open(site_name)
                return f"E HAPA {site_name} për ty, Boss!"
            webbrowser.open(f"https://www.{site_name}.com")
            return f"PO HAP {site_name.upper()} për ty, Boss!"

    # KËRKO NË GOOGLE
    if any(w in lower for w in ["kerko", "kërko", "search", "gjej", "shiko ne", "shiko në"]):
        query = lower
        for word in ["kerko", "kërko", "search", "gjej", "shiko ne", "shiko në", "ne google", "në google", "per", "për"]:
            query = query.replace(word, "")
        query = query.strip().strip("?").strip(".")
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"PO KËRKOJ \"{query}\" në Google për ty, Boss!"

    # HIQ TË GJITHA EVENTET
    if "hiq" in lower and ("te gjitha" in lower or "gjitha" in lower or "all" in lower):
        remove_calendar_events()
        return "Fshiva të gjitha eventet nga agjenda, Boss!"

    # SHIKOJE DHE REGJISTRO (pattern i ndërlikuar)
    # P.sh. "shikoje nëse kam diçka dhe nëse s'ka regjistroje për të shtunën..."
    if ("shikoje" in lower or "shiko" in lower or "kontrollo" in lower) and ("regjistro" in lower or "shto" in lower or "vendos" in lower):
        date_str = parse_date(lower)
        time_str = parse_time(lower)
        existing = get_events_for_date(date_str) if date_str else get_today_events()
        if existing:
            lines = [f"• {e.get('time', '--:--')} - {e['title']}" for e in existing]
            return f"Ke tashmë {len(existing)} evente për këtë ditë:\n" + "\n".join(lines) + "\n\nA don me shtu diçka tjetër, Boss?"
        # Nuk ka evente — provo me regjistru
        detail = lower
        for word in ["shikoje", "shiko", "kontrollo", "nese", "nëse", "ska", "s'ka", "ka", "dhe", "per", "për", "ne", "në", "agjende", "agjendë", "dite", "ditë", "tjetër", "tjeter"]:
            detail = detail.replace(word, "")
        for phrase in cleanup_phrases:
            detail = detail.replace(phrase, "")
        detail = re.sub(r'\s+', ' ', detail).strip()
        detail = detail.strip('.,;:!?')
        if detail and len(detail) > 2:
            add_calendar_event(detail, date_str, time_str)
            date_label = "nesër" if "neser" in lower or "nesër" in lower else "sot"
            if "shtun" in lower:
                date_label = "të shtunën"
            return f"S'ke asgjë për këtë ditë. E regjistruar: '{detail}' për {date_label}, Boss!"
        return "Nuk ke asgjë të planifikuar. Ça don me shtu, Boss?"

    # SHTO/KRIJO EVENT - të gjitha variacionet
    shto_words = ["shto", "shtoje", "shtone", "krijo", "krijoj", "krijoje", "regjistro", "regjistroje", "regjistron", "mbaj", "vendos", "vendose", "sheno", "shëno", "shenoje", "regjistrom"]
    event_words = ["agjend", "agjenden", "agjenda", "event", "events", "aktivitet", "takim", "takimin", "takimi", "mbledhje", "mbledhjen", "detyr", "detyren", "takimi"]
    
    # Clean-up phrases to remove from event detail
    cleanup_phrases = [
        "ne agjende", "ne agjend", "ne agjenden", "ne calendar", "ne kalendar",
        "agjenden time", "agjenda ime", "listen time", "listën time",
        "per te shtunen", "per neser", "per sot", "për nesër", "për sot", "për të shtunën",
        "te shtunen", "të shtunën", "nesër", "sot",
        "kete", "këtë", "ketu", "këtu",
        "regjistroje", "regjistron", "shtoje", "krijoje",
        "n time", "n agjende", "ne listen"
    ]
    
    if any(w in lower for w in shto_words) and any(w in lower for w in event_words):
        date_str = parse_date(lower)
        time_str = parse_time(lower)
        
        for word in shto_words:
            if word in lower:
                parts = lower.split(word, 1)
                if len(parts) > 1:
                    detail = parts[1].strip()
                    # Remove leading noise words
                    detail = re.sub(r'^(je|e|per|për|ne|në|te|të|këtë|kete|takim|event|agjend)\s+', '', detail)
                    for phrase in cleanup_phrases:
                        detail = detail.replace(phrase, "").strip()
                    
                    detail = re.sub(r'\s+', ' ', detail).strip()
                    detail = detail.strip('.,;:!?')
                    if detail and len(detail) > 1:
                        add_calendar_event(detail, date_str, time_str)
                        time_label = f" në {time_str}" if time_str else ""
                        date_label = "nesër" if "neser" in lower or "nesër" in lower else "sot"
                        if "shtun" in lower:
                            date_label = "të shtunën"
                        return f"E regjistruar: '{detail}'{time_label} për {date_label}, Boss!"
                return "Si don ta quajtësh aktivitetin?"

    # SHIKO AGJENDËN
    if any(w in lower for w in ["agjenda", "agjend", "calendar", "kalendar", "aktivitetet", "eventet", "event", "takimet", "takim", "mbledhjet", "mbledhje", "detyrat", "detyra", "planin", "plani", "çka kam", "cka kam", "çka po", "cka po", "si eshte dita", "si është dita", "si kaloi", "programin", "programi", "agjenda ime"]):
        target_date = parse_date(lower)
        events = get_events_for_date(target_date)
        date_label = "nesër" if "neser" in lower or "nesër" in lower else "sot"
        if "shtun" in lower:
            date_label = "të shtunën"
        elif "hene" in lower or "hën" in lower:
            date_label = "të hënën"
        elif "marten" in lower or "mart" in lower:
            date_label = "të martën"
        elif "merkur" in lower:
            date_label = "të mërkurën"
        elif "enjte" in lower:
            date_label = "të enjten"
        elif "premte" in lower:
            date_label = "të premten"
        elif "diel" in lower:
            date_label = "të dielën"
        if events:
            lines = [f"• {e.get('time', '--:--')} - {e['title']}" for e in events]
            return f"Agjenda për {date_label} ({len(events)} aktivitete):\n" + "\n".join(lines) + "\n\nA ke ndonjë gjë tjetër, Boss?"
        return f" për {date_label} nuk ke asgjë në agjendë, Boss!"

    # ORA - vetëm për pyetje të thjeshta për orën
    now = datetime.datetime.now()
    if any(w in lower for w in ["sa eshte ora", "sa është ora", "cila eshte ora", "cilat eshte ora"]):
        return f"Ora aktuale është {now.strftime('%H:%M')}, Boss!"

    # DATA
    if any(w in lower for w in ["data", "daten", "datën", "cila dite", "cilën ditë"]):
        days = ["e hënë", "e martë", "e mërkurë", "e enjte", "e premte", "e shtunë", "e diel"]
        return f"Sot është {days[now.weekday()]}, {now.strftime('%d.%m.%Y')}, Boss!"

    # LLOGARITJE
    if any(w in lower for w in ["math", "llogarit", "sa bejne", "sa bëjnë", "sa eshte", "sa është"]):
        expr = re.sub(r'[^0-9+\-*/().%\s]', '', lower)
        try:
            result = eval(expr)
            return f"Rezultati është: {result}, Boss!"
        except:
            pass

    # FALËNDERIM
    if any(w in lower for w in ["flm", "faleminderit", "thanks", "faleminderit"]):
        return "Nuk ka për çfarë, Boss! Jam gjithmonë këtu për ty."

    # MIRËMËNGJES
    if any(w in lower for w in ["miremengjes", "mirëmëngjes", "good morning"]):
        return "Mirëmëngjes, Boss! Si kalove natën?"

    # MIRËMBREMA
    if any(w in lower for w in ["mirembrame", "mirëmbrëma", "good evening"]):
        return "Mirëmbrëma, Boss! Si shkoi dita?"

    return None


@app.post("/api/chat")
async def chat(msg: ChatMessage):
    command_reply = detect_command(msg.message)
    if command_reply:
        return {"reply": command_reply}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in msg.history[-20:]:
        messages.append(h)
    messages.append({"role": "user", "content": msg.message})

    # Try OpenRouter first
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            return {"reply": reply}
    except Exception as e:
        print(f"[OpenRouter ERROR] {e}")

    # Fallback to Ollama
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": MODEL, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            reply = data["message"]["content"]
            return {"reply": reply}
    except Exception as e:
        print(f"[Ollama ERROR] {e}")

    return {"reply": "Boss, kam problem me lidhjen. Provoni përsëri."}


@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    tmp_input = None
    tmp_wav = None
    try:
        audio_bytes = await audio.read()
        print(f"[STT] Received: {len(audio_bytes)} bytes, type={audio.content_type}")

        if len(audio_bytes) < 100:
            return {"text": "", "error": "Audio shume i vogel."}

        ext = ".webm"
        if audio.content_type:
            if "mp4" in audio.content_type:
                ext = ".mp4"
            elif "ogg" in audio.content_type:
                ext = ".ogg"
            elif "wav" in audio.content_type:
                ext = ".wav"

        tmp_input = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp_input.write(audio_bytes)
        tmp_input.close()

        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav.close()

        print(f"[STT] Converting {ext} -> wav...")
        result = subprocess.run(
            [FFMPEG, "-i", tmp_input.name, "-ar", "16000", "-ac", "1", "-f", "wav", tmp_wav.name, "-y"],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            print(f"[STT] ffmpeg error: {result.stderr[:200]}")
            return {"text": "", "error": "Gabim ne konvertimin e audios."}

        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_wav.name) as source:
            audio_data = recognizer.record(source)

        print("[STT] Sending to Google (sq-AL)...")
        text = recognizer.recognize_google(audio_data, language="sq-AL")
        print(f"[STT] Result: {text}")

        return {"text": text}

    except sr.UnknownValueError:
        return {"text": "", "error": "Nuk degjova asgje. Provo perseri."}
    except sr.RequestError:
        return {"text": "", "error": "Gabim ne Google API."}
    except subprocess.TimeoutExpired:
        return {"text": "", "error": "Konvertimi mori shume kohe."}
    except Exception as e:
        print(f"[STT] Error: {e}")
        traceback.print_exc()
        return {"text": "", "error": f"Gabim: {str(e)}"}
    finally:
        if tmp_input and os.path.exists(tmp_input.name):
            os.unlink(tmp_input.name)
        if tmp_wav and os.path.exists(tmp_wav.name):
            os.unlink(tmp_wav.name)


@app.post("/api/text-to-speech")
async def text_to_speech(data: dict):
    text = data.get("text", "")
    if not text:
        return JSONResponse({"error": "No text"}, status_code=400)

    try:
        communicate = edge_tts.Communicate(text, VOICE, rate="-5%", pitch="+2Hz")
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        await communicate.save(tmp.name)

        audio_bytes = open(tmp.name, "rb").read()
        os.unlink(tmp.name)

        return JSONResponse(content={"audio": list(audio_bytes), "type": "audio/mpeg"})

    except Exception as e:
        print(f"[TTS] Error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": OPENROUTER_MODEL, "provider": "openrouter"}


@app.get("/api/calendar")
async def get_calendar():
    cal = load_calendar()
    today = datetime.date.today().isoformat()
    events = cal.get("events", [])
    today_events = [e for e in events if e.get("date") == today]
    return {"events": events, "today": today_events, "today_date": today}


@app.post("/api/calendar")
async def add_event(data: dict):
    title = data.get("title", "")
    date_str = data.get("date", datetime.date.today().isoformat())
    time_str = data.get("time", "")
    if title:
        add_calendar_event(title, date_str, time_str)
        return {"ok": True, "message": f"E shtova '{title}' në agjendë!"}
    return {"ok": False, "message": "Jep emrin e aktivitetit, Boss!"}


@app.delete("/api/calendar")
async def clear_calendar():
    remove_calendar_events()
    return {"ok": True, "message": "Fshiva të gjitha eventet!"}


frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    print("JARVIS starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
