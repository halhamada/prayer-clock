"""Run from the project root: python -m unittest discover tests"""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
_tmp = tempfile.TemporaryDirectory()
os.environ["PRAYER_DATA"] = _tmp.name
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import arabic
import clockface
import hijri
import output
import player
import prayertimes
import schedule
import server
import settings

CFG = settings.DEFAULTS
SAMPLE = date(2026, 1, 30)


def clear_audio():
    settings.AUDIO.mkdir(parents=True, exist_ok=True)
    for f in settings.AUDIO.iterdir():
        f.unlink()


def add_files(*names):
    for n in names:
        (settings.AUDIO / n).write_bytes(b"x")


class FakePlayer:
    def __init__(self):
        self.played = []
        self.busy = False

    def play(self, path, title):
        self.played.append((Path(path).name, title))

    def is_playing(self):
        return self.busy


class Times(unittest.TestCase):
    def test_same_day_as_the_wall_clock_photo(self):
        t = prayertimes.compute(SAMPLE, CFG["latitude"], CFG["longitude"], 3)
        self.assertAlmostEqual(t[prayertimes.MAGHRIB] * 60, 17 * 60 + 39, delta=1)
        self.assertAlmostEqual(t[prayertimes.SUNRISE] * 60, 6 * 60 + 26, delta=2)

    def test_hijri_matches_umm_al_qura(self):
        self.assertEqual(hijri.of(SAMPLE), (1447, 8, 11))
        self.assertEqual(hijri.of(SAMPLE, -1), (1447, 8, 10))
        self.assertEqual(hijri.of(date(2026, 10, 31)), (1448, 5, 20))

    def test_next_prayer_rolls_over_to_tomorrow(self):
        key, left = clockface.next_prayer(datetime(2026, 1, 30, 12, 52, 5), CFG)
        self.assertEqual(key, "maghrib")
        self.assertAlmostEqual(left, 4 * 3600 + 47 * 60, delta=120)
        key, left = clockface.next_prayer(datetime(2026, 1, 30, 22, 0, 0), CFG)
        self.assertEqual(key, "fajr")
        self.assertGreater(left, 6 * 3600)


class Arabic(unittest.TestCase):
    def test_joining(self):
        self.assertEqual(arabic.shape("لا"), "ﻻ")
        self.assertEqual(arabic.shape("بب"), "ﺑﺐ")
        self.assertEqual(arabic.shape("ب"), "ﺏ")

    def test_numbers_stay_readable_in_a_right_to_left_line(self):
        line = arabic.visual("شعبان 10")
        self.assertTrue(line.startswith("10 "))

    def test_latin_untouched(self):
        self.assertEqual(arabic.visual("Fri, Jan 30, 2026"), "Fri, Jan 30, 2026")

    def test_font_has_every_form(self):
        pygame.font.init()
        font = pygame.font.Font(str(clockface.FONTS / "plex_arabic_bold.ttf"), 20)
        forms = [f for group in arabic._FORMS.values() for f in group] + list(arabic._LAM_ALEF.values())
        for ch, metric in zip(forms, font.metrics("".join(forms))):
            self.assertIsNotNone(metric, hex(ord(ch)))


class Schedule(unittest.TestCase):
    def setUp(self):
        clear_audio()
        add_files("azan.mp3", "komail.mp3", "kisa.mp3", "thu.mp3")
        self.schedule = {
            "adhan": {"file": "azan.mp3", "prayers": ["fajr", "dhuhr", "maghrib"]},
            "daily": {"thu": "thu.mp3"},
            "items": [
                {"id": "a", "title": "دعاء كميل", "file": "komail.mp3", "at": "prayer", "prayer": "maghrib",
                 "offset": 15, "days": [4]},
                {"id": "b", "title": "حديث الكساء", "file": "kisa.mp3", "at": "clock", "time": "15:00", "days": []},
                {"id": "c", "title": "دعاء اليوم", "file": "@daily", "at": "clock", "time": "16:00", "days": []},
                {"id": "d", "title": "معطل", "file": "kisa.mp3", "at": "clock", "time": "17:00", "enabled": False},
            ]}
        schedule.save(self.schedule)
        self.thursday, self.friday = date(2026, 1, 29), date(2026, 1, 30)

    def test_reference_schedule_file_loads(self):
        s = json.loads((ROOT / "audio" / "schedule.json").read_text(encoding="utf-8"))
        add_files("tawasel.mp3")
        s["adhan"]["file"] = "azan.mp3"
        self.assertTrue(schedule.events(s, self.thursday, CFG))

    def test_days_daily_and_disabled(self):
        thu = [e.title for e in schedule.events(self.schedule, self.thursday, CFG)]
        fri = [e.title for e in schedule.events(self.schedule, self.friday, CFG)]
        self.assertIn("دعاء كميل", thu)
        self.assertIn("دعاء اليوم", thu)
        self.assertNotIn("دعاء كميل", fri)
        self.assertNotIn("دعاء اليوم", fri)   # no file for Friday
        self.assertNotIn("معطل", thu)

    def _at(self, day, minute):
        return datetime(day.year, day.month, day.day, minute // 60, minute % 60)

    def test_adhan_cuts_in_and_fires_once(self):
        p = FakePlayer()
        p.busy = True
        s = schedule.Scheduler(p)
        m = schedule.prayer_minutes(self.friday, CFG)["dhuhr"]
        s.tick(self._at(self.friday, m), CFG)
        s.tick(self._at(self.friday, m + 1), CFG)
        self.assertEqual(p.played, [("azan.mp3", "أذان الظهر")])

    def test_late_tick_still_fires_but_a_stale_one_does_not(self):
        p = FakePlayer()
        m = schedule.prayer_minutes(self.friday, CFG)["dhuhr"]
        schedule.Scheduler(p).tick(self._at(self.friday, m + 2), CFG)
        self.assertEqual(len(p.played), 1)
        p = FakePlayer()
        schedule.Scheduler(p).tick(self._at(self.friday, m + 3), CFG)
        self.assertEqual(p.played, [])

    def test_dua_waits_for_the_player_and_gives_up_after_two_hours(self):
        p = FakePlayer()
        p.busy = True
        s = schedule.Scheduler(p)
        s.tick(self._at(self.friday, 15 * 60), CFG)
        self.assertEqual(p.played, [])
        p.busy = False
        s.tick(self._at(self.friday, 15 * 60 + 30), CFG)
        self.assertEqual(p.played, [("kisa.mp3", "حديث الكساء")])

        p = FakePlayer()
        p.busy = True
        s = schedule.Scheduler(p)
        s.tick(self._at(self.friday, 15 * 60), CFG)
        p.busy = False
        s.tick(self._at(self.friday, 15 * 60 + 121), CFG)
        self.assertEqual(p.played, [])


class Screen(unittest.TestCase):
    def setUp(self):
        pygame.font.init()

    def _frame(self, size):
        surface = output.logical_surface(size)
        clockface.Face(*size).draw(surface, datetime(2026, 1, 30, 12, 52, 5), CFG, "أذان الظهر", "تحذير")
        return surface

    def test_every_layout_draws(self):
        for size in ((720, 1280), (1280, 720), (1080, 1920)):
            self.assertGreater(self._frame(size).get_at((size[0] // 2, size[1] // 2)).b, 0)

    def test_framebuffer_formats_and_rotation(self):
        for bpp, stride in ((16, 2560), (32, 5120), (32, 5200)):
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(b"\0" * (stride * 720))
            fb = output.Framebuffer(1280, 720, bpp, stride, f.name)
            size = fb.logical_size(90)
            self.assertEqual(size, (720, 1280))
            fb.show(self._frame(size), 90)
            fb.file.close()
            written = Path(f.name).read_bytes()
            os.unlink(f.name)
            self.assertEqual(len(written), stride * 720)
            self.assertTrue(any(written))


class Player(unittest.TestCase):
    def test_volume_and_device(self):
        self.assertEqual(player.command("a.mp3", {"volume": 50}), ["mpg123", "-q", "-f", "16384", "a.mp3"])
        cmd = player.command("a.mp3", {"volume": 100, "audio_device": "default:CARD=vc4hdmi"})
        self.assertEqual(cmd[-3:], ["-a", "default:CARD=vc4hdmi", "a.mp3"])


class Dashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Clock:
            def synced(self):
                return True

            def set(self, epoch):
                return True

        class App:
            auth = server.Auth()
            clock = Clock()

            class player:
                played = []

                @staticmethod
                def title():
                    return ""

                @classmethod
                def play(cls, path, title):
                    cls.played.append(path)

                @staticmethod
                def stop():
                    pass

        cls.app = App
        cls.http = server.start(App, 0)
        cls.base = f"http://127.0.0.1:{cls.http.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()

    def call(self, path, body=None, pin="1234", raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method="POST" if data is not None else "GET",
                                     headers={"X-Pin": pin} if pin else {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_flow(self):
        clear_audio()
        self.assertEqual(self.call("/api/state", pin=None)[0], 401)
        self.assertEqual(self.call("/api/pin", {"pin": "12"}, pin=None)[0], 400)
        self.assertEqual(self.call("/api/pin", {"pin": "1234"}, pin=None)[0], 200)
        self.assertEqual(self.call("/api/pin", {"pin": "9999"}, pin=None)[0], 401)   # taken by the first visitor
        self.assertFalse(b"1234" in (settings.DATA / "auth.json").read_bytes())
        self.assertEqual(self.call("/api/state")[0], 200)

        code, body = self.call("/api/upload?name=adhan.mp3", raw=b"abc")
        self.assertEqual((code, json.loads(body)["name"]), (200, "adhan.mp3"))
        self.assertEqual(self.call("/api/upload?name=x.m4a", raw=b"abc")[0], 400)
        code, body = self.call("/api/upload?name=" + urllib.request.quote("../../evil.mp3"), raw=b"abc")
        self.assertEqual(json.loads(body)["name"], "evil.mp3")
        self.assertTrue((settings.AUDIO / "evil.mp3").is_file())

        self.assertEqual(self.call("/api/test?name=adhan.mp3", raw=b"")[0], 200)
        self.assertEqual(self.call("/api/test?name=../config.json", raw=b"")[0], 404)
        self.assertEqual(self.call("/api/test?name=schedule.json", raw=b"")[0], 404)

        code, body = self.call("/api/settings", {"volume": 70, "rotate": 0, "prayer_offsets": {"fajr": -8, "x": 3}})
        self.assertEqual(code, 200)
        cfg = json.loads(body)["settings"]
        self.assertEqual((cfg["volume"], cfg["rotate"], cfg["prayer_offsets"]), (70, 0, {"fajr": -8}))
        self.assertEqual(self.call("/api/settings", {"rotate": 45})[0], 400)
        settings.save({"rotate": 90, "prayer_offsets": {}})

        self.assertEqual(self.call("/api/delete?name=evil.mp3", raw=b"")[0], 200)
        self.assertFalse((settings.AUDIO / "evil.mp3").exists())
        self.assertIn("ساعة الصلاة".encode(), self.call("/", pin=None)[1])

    def test_zz_lockout_after_five_wrong_pins(self):
        self.assertEqual(self.call("/api/state")[0], 200)
        for _ in range(5):
            self.assertEqual(self.call("/api/state", pin="0000")[0], 401)
        self.assertEqual(self.call("/api/state")[0], 401)
        self.app.auth.locked_until = 0


if __name__ == "__main__":
    unittest.main()
