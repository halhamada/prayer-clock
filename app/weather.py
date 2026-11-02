"""Current weather from Open-Meteo (free, no account) for the photo face, fetched at most once an hour and kept in
weather.json in the data dir, so the screen shows the last reading at once and nothing if the device has never been
online. A port of Weather.java from the MITV launcher."""

import json
import threading
import time
import urllib.request

import settings

MAX_AGE = 60 * 60
RETRY = 10 * 60

_lock = threading.Lock()
_busy = False
_tried = 0


def _path():
    return settings.DATA / "weather.json"


def reading():
    """{"temp", "max", "min", "code"} from the last fetch, or None."""
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def refresh(lat, lng):
    """Fetches in the background when the saved reading is over an hour old."""
    global _busy, _tried
    r = reading()
    now = time.time()
    with _lock:
        if _busy or (r and now - r.get("at", 0) < MAX_AGE) or now - _tried < RETRY:
            return
        _busy, _tried = True, now
    threading.Thread(target=_fetch, args=(lat, lng), name="weather", daemon=True).start()


def _fetch(lat, lng):
    global _busy
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lng:.4f}"
               "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min"
               "&timezone=auto&forecast_days=1")
        with urllib.request.urlopen(url, timeout=10) as f:
            j = json.load(f)
        settings.write_json(_path(), {
            "temp": round(j["current"]["temperature_2m"]), "code": int(j["current"]["weather_code"]),
            "max": round(j["daily"]["temperature_2m_max"][0]), "min": round(j["daily"]["temperature_2m_min"][0]),
            "at": time.time()})
    except Exception as e:   # offline or the service is down: keep the last reading, try again later
        print("weather:", repr(e), flush=True)
    finally:
        _busy = False


def describe(code):
    """WMO weather code to a short Arabic description."""
    if code == 0:
        return "صافٍ"
    if code <= 2:
        return "غائم جزئياً"
    if code == 3:
        return "غائم"
    if code in (45, 48):
        return "ضباب"
    if 51 <= code <= 57:
        return "رذاذ"
    if 61 <= code <= 67:
        return "ماطر"
    if 71 <= code <= 77:
        return "ثلوج"
    if 80 <= code <= 82:
        return "زخات مطر"
    if code >= 95:
        return "عاصفة رعدية"
    return ""
