"""Where the data lives and the device settings edited from the dashboard (config.json in the data dir)."""

import json
import os
from pathlib import Path

DATA = Path(os.environ.get("PRAYER_DATA", Path(__file__).resolve().parent.parent / "data"))
AUDIO = Path(os.environ.get("PRAYER_AUDIO", DATA / "audio"))

DEFAULTS = {
    "city": "الأحساء",
    "latitude": 25.3833,
    "longitude": 49.5858,
    "rotate": 90,            # 0 for a landscape TV; 90 or 270 for one hung upright
    "hijri_offset": 0,       # days added to the Umm al-Qura date
    "volume": 100,           # percent of full scale; 100 leaves the audio as recorded
    "muted": False,          # nothing scheduled plays while set; tests from the dashboard still do
    "audio_device": "default:CARD=vc4hdmi",   # the TV; the Pi 3's system default is its headphone jack
    "prayer_offsets": {},    # minutes added to a prayer, like {"fajr": 2}
}

_cache = None
_stamp = None


def write_json(path, value):
    """Writes through a temp file and fsyncs, so a power cut leaves the old file or the new one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load():
    """The settings, re-read only when the file changed since the last call."""
    global _cache, _stamp
    path = DATA / "config.json"
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        stamp = None
    if _cache is None or stamp != _stamp:
        saved = {}
        if stamp is not None:
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                print("config.json unreadable, using defaults:", e, flush=True)
        _cache = {**DEFAULTS, **saved}
        _stamp = stamp
    return _cache


def save(changes):
    """Merges changes into the file; returns the new settings."""
    write_json(DATA / "config.json", {**load(), **changes})
    return load()
