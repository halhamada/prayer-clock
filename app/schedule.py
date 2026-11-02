"""The audio schedule edited from the dashboard: the adhan (file and which prayers), one dua file per weekday, and
timed items. Same schedule.json as the MITV launcher, kept next to the audio files, so a schedule and its files
can be copied between the devices as they are."""

import json
import math
from collections import namedtuple
from datetime import datetime

import prayertimes
import settings

PRAYER_KEYS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")
PRAYER_NAMES = ("الفجر", "الشروق", "الظهر", "العصر", "المغرب", "العشاء")
_PRAYER_INDEX = (prayertimes.FAJR, prayertimes.SUNRISE, prayertimes.DHUHR,
                 prayertimes.ASR, prayertimes.MAGHRIB, prayertimes.ISHA)
DAY_KEYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")   # index is weekday, Sunday first
DAILY = "@daily"
MAX_WAIT_MIN = 120
LATE_MIN = 2

Event = namedtuple("Event", "key title file minute interrupt adhan")


def load():
    try:
        return json.loads((settings.AUDIO / "schedule.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"adhan": {"file": "", "prayers": ["fajr", "dhuhr", "maghrib"]}, "daily": {}, "items": []}


def save(schedule):
    settings.write_json(settings.AUDIO / "schedule.json", schedule)


def zone_hours(date):
    return datetime(date.year, date.month, date.day, 12).astimezone().utcoffset().total_seconds() / 3600


def prayer_minutes(date, cfg):
    """The day's prayer times as minutes after midnight, as a dict by key."""
    t = prayertimes.compute(date, cfg["latitude"], cfg["longitude"], zone_hours(date))
    offsets = cfg.get("prayer_offsets") or {}
    return {k: math.floor(t[_PRAYER_INDEX[i]] * 60 + 0.5) + int(offsets.get(k, 0))
            for i, k in enumerate(PRAYER_KEYS)}


def weekday(date):
    return date.isoweekday() % 7


def events(s, date, cfg):
    """Everything scheduled on date, in time order."""
    pm = prayer_minutes(date, cfg)
    dow = weekday(date)
    out = []

    adhan = s.get("adhan") or {}
    file = adhan.get("file") or ""
    if file and (settings.AUDIO / file).is_file():
        for k in adhan.get("prayers") or []:
            if k in pm:
                out.append(Event(f"{date}|adhan|{k}", "أذان " + PRAYER_NAMES[PRAYER_KEYS.index(k)],
                                 file, pm[k], True, True))

    for it in s.get("items") or []:
        if not it.get("enabled", True):
            continue
        days = it.get("days") or []
        if days and dow not in days:
            continue
        if it.get("at") == "prayer":
            if it.get("prayer") not in pm:
                continue
            minute = pm[it["prayer"]] + int(it.get("offset") or 0)
        else:
            try:
                h, m = str(it.get("time", "")).split(":")
                minute = int(h) * 60 + int(m)
            except ValueError:
                continue
        if not 0 <= minute < 24 * 60:
            continue
        file = it.get("file") or ""
        if file == DAILY:
            file = (s.get("daily") or {}).get(DAY_KEYS[dow], "")
        if not file or not (settings.AUDIO / file).is_file():
            continue
        out.append(Event(f"{date}|{it.get('id', '')}|{minute}", it.get("title") or "دعاء", file, minute,
                         bool(it.get("interrupt")), False))
    out.sort(key=lambda e: e.minute)
    return out


class Scheduler:
    """Checked once a minute: an interrupting item (the adhan) plays at once, over anything; a dua waits for
    whatever is playing to end, for up to two hours."""

    def __init__(self, player):
        self.player = player
        self.fired = set()
        self.waiting = []
        self.fired_for = None

    def tick(self, now, cfg):
        today = now.date()
        if today != self.fired_for:
            self.fired_for = today
            self.fired.clear()
            self.waiting.clear()
        minute = now.hour * 60 + now.minute
        for e in events(load(), today, cfg):
            # A tick can run a minute late; anything due in the last two minutes still counts.
            if e.minute > minute or minute - e.minute > LATE_MIN or e.key in self.fired:
                continue
            self.fired.add(e.key)
            if cfg.get("muted"):
                continue
            if e.interrupt:
                self._play(e)
            else:
                self.waiting.append(e)
        self.waiting = [e for e in self.waiting if minute - e.minute <= MAX_WAIT_MIN and not cfg.get("muted")]
        if self.waiting and not self.player.is_playing():
            self._play(self.waiting.pop(0))   # one at a time; the next waits for a following tick

    def _play(self, e):
        self.player.play(settings.AUDIO / e.file, e.title)
