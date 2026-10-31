"""The audio dashboard, a page served on the home network (http://device:8080) for managing the adhan and duas from a
phone or laptop. Plain HTTP with a PIN the first visitor sets; after five wrong PINs the API locks for five minutes.
The page itself is dashboard.html; everything else is /api/*."""

import hashlib
import hmac
import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

import clockface
import player as player_module
import schedule
import settings

PORT = 8080
MAX_UPLOAD = 200 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
AUDIO_TYPES = (".mp3", ".wav")   # what mpg123 decodes
PAGE = Path(__file__).with_name("dashboard.html")


class Auth:
    """The PIN, salted and hashed in auth.json in the data dir, and the lockout after wrong tries."""

    def __init__(self):
        self.path = settings.DATA / "auth.json"
        self.failures = 0
        self.locked_until = 0
        self.lock = threading.Lock()

    def _stored(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _hash(pin, salt):
        return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 20000).hex()

    def is_set(self):
        return self._stored() is not None

    def set(self, pin):
        salt = os.urandom(16).hex()
        settings.write_json(self.path, {"salt": salt, "hash": self._hash(pin, salt)})

    def check(self, pin):
        stored = self._stored()
        with self.lock:
            if stored is None or pin is None or time.time() < self.locked_until:
                return False
            if hmac.compare_digest(self._hash(pin, stored["salt"]), stored["hash"]):
                self.failures = 0
                return True
            self.failures += 1
            if self.failures >= 5:
                self.failures = 0
                self.locked_until = time.time() + 5 * 60
            return False


def safe_name(requested):
    """Keeps letters, digits, dash and underscore; anything else (Arabic names too) becomes a timestamped name."""
    ext = Path(requested).suffix.lower()
    if ext not in AUDIO_TYPES:
        return None
    base = re.sub(r"[^A-Za-z0-9_-]", "", Path(requested).stem) or f"audio_{int(time.time() * 1000)}"
    name = base + ext
    i = 2
    while (settings.AUDIO / name).exists():
        name = f"{base}_{i}{ext}"
        i += 1
    return name


def audio_file(name):
    """The audio file called name, or None if that is not a plain file name in the audio dir."""
    if not name or name != Path(name).name or name.startswith("schedule.json"):
        return None
    path = settings.AUDIO / name
    return path if path.is_file() else None


def hhmm(minute):
    m = minute % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def state(app):
    cfg = settings.load()
    s = schedule.load()
    settings.AUDIO.mkdir(parents=True, exist_ok=True)
    files = [{"name": f.name, "size": f.stat().st_size}
             for f in sorted(settings.AUDIO.iterdir(), key=lambda f: f.name.lower())
             if f.is_file() and f.suffix.lower() in AUDIO_TYPES]
    today = datetime.now().date()
    pm = schedule.prayer_minutes(today, cfg)
    upcoming = [{"day": d, "time": hhmm(e.minute), "title": e.title, "file": e.file, "adhan": e.adhan}
                for d in range(2) for e in schedule.events(s, today + timedelta(days=d), cfg)]
    return {"schedule": s, "files": files, "prayers": {k: hhmm(v) for k, v in pm.items()}, "upcoming": upcoming,
            "today": str(today), "weekday": schedule.weekday(today), "settings": cfg,
            "devices": player_module.devices(), "playing": app.player.title(),
            "clockSynced": app.clock.synced(), "hijri": clockface.hijri_line(today, cfg)}


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *args):
            pass

        def _send(self, code, body, kind="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, value):
            self._send(code, json.dumps(value, ensure_ascii=False).encode())

        def _error(self, code, message):
            self._json(code, {"error": message})

        def _length(self):
            return int(self.headers.get("Content-Length") or 0)

        def _body(self):
            length = self._length()
            if length > MAX_JSON:
                raise ValueError("body too large")
            return json.loads(self.rfile.read(length).decode())

        def _authorised(self):
            given = self.headers.get("X-Pin")
            return app.auth.check(unquote(given)) if given else False

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path in ("/", "/index.html"):
                self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/state":
                pin_set = app.auth.is_set()
                if self._authorised():
                    self._json(200, {**state(app), "pinSet": pin_set})
                else:
                    self._json(401, {"pinSet": pin_set})
            else:
                self._error(404, "not found")

        def do_POST(self):
            url = urlsplit(self.path)
            query = dict(parse_qsl(url.query))
            try:
                self._route(url.path, query)
            except (ValueError, KeyError, TypeError):
                self._error(400, "طلب غير صحيح")

        def _route(self, path, query):
            if path == "/api/pin":
                pin = str(self._body().get("pin", ""))
                if len(pin) < 4:
                    return self._error(400, "الرمز لازم يكون 4 أرقام أو أكثر")
                if app.auth.is_set() and not self._authorised():
                    return self._error(401, "الرمز الحالي غلط")
                app.auth.set(pin)
                return self._json(200, {"ok": True})
            if not self._authorised():
                return self._json(401, {"error": "الرمز غلط", "pinSet": app.auth.is_set()})

            if path == "/api/schedule":
                s = self._body()
                if not isinstance(s, dict):
                    raise ValueError("schedule")
                schedule.save(s)
                return self._json(200, state(app))
            if path == "/api/settings":
                return self._json(200, self._settings(self._body()))
            if path == "/api/upload":
                return self._upload(query.get("name", ""))
            if path == "/api/delete":
                f = audio_file(query.get("name"))
                if f:
                    f.unlink()
                return self._json(200, state(app))
            if path == "/api/test":
                f = audio_file(query.get("name"))
                if not f:
                    return self._error(404, "الملف مو موجود")
                app.player.play(f, query.get("title", "تجربة"))
                return self._json(200, {"ok": True})
            if path == "/api/stop":
                app.player.stop()
                return self._json(200, {"ok": True})
            if path == "/api/time":
                return self._set_time(self._body())
            self._error(404, "not found")

        def _settings(self, body):
            changes = {}
            if "city" in body:
                changes["city"] = str(body["city"])[:40]
            if "latitude" in body:
                changes["latitude"] = _bounded(body["latitude"], -66, 66)
            if "longitude" in body:
                changes["longitude"] = _bounded(body["longitude"], -180, 180)
            if "rotate" in body:
                if int(body["rotate"]) not in (0, 90, 180, 270):
                    raise ValueError("rotate")
                changes["rotate"] = int(body["rotate"])
            if "hijri_offset" in body:
                changes["hijri_offset"] = int(_bounded(body["hijri_offset"], -3, 3))
            if "volume" in body:
                changes["volume"] = int(_bounded(body["volume"], 0, 100))
            if "audio_device" in body:
                changes["audio_device"] = str(body["audio_device"])
            if "prayer_offsets" in body:
                changes["prayer_offsets"] = {k: int(_bounded(v, -60, 60)) for k, v in body["prayer_offsets"].items()
                                             if k in schedule.PRAYER_KEYS and int(v)}
            settings.save(changes)
            return state(app)

        def _upload(self, requested):
            length = self._length()
            if length <= 0 or length > MAX_UPLOAD:
                return self._error(400, "الملف فاضي أو أكبر من 200 ميجا")
            name = safe_name(requested)
            if not name:
                return self._error(400, "الجهاز يشغّل MP3 و WAV فقط، حوّل الملف إلى MP3")
            settings.AUDIO.mkdir(parents=True, exist_ok=True)
            part = settings.AUDIO / (name + ".part")
            left = length
            with open(part, "wb") as f:
                while left > 0:
                    chunk = self.rfile.read(min(64 * 1024, left))
                    if not chunk:
                        break
                    f.write(chunk)
                    left -= len(chunk)
            if left > 0:
                part.unlink()
                return self._error(400, "انقطع الرفع")
            os.replace(part, settings.AUDIO / name)
            return self._json(200, {"name": name})

        def _set_time(self, body):
            if not app.clock.set(int(body["epoch"])):
                return self._error(500, "تعذر ضبط الوقت")
            return self._json(200, state(app))

    return Handler


def _bounded(value, low, high):
    v = float(value)
    if not low <= v <= high:
        raise ValueError("out of range")
    return v


def set_system_time(epoch):
    """Through the sudo rule setup.sh installs for exactly this command."""
    result = subprocess.run(["sudo", "-n", "/usr/bin/date", "-s", f"@{epoch}"], capture_output=True, timeout=10)
    return result.returncode == 0


def start(app, port=PORT):
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(app))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name="dashboard", daemon=True).start()
    return server
