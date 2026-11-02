"""The photo face, the clock screen of the MITV launcher on the TCL and Mi Box: a photo of the shrines that follows
the time of day and moves on at every adhan, the day with its Gregorian and Hijri dates, a large time, the weather,
the next prayer with the time left to it over the day's six times, and the days to Ramadan. Laid out like the TV
in landscape, and stacked for a screen hung upright.

Sizes are in the launcher's dp, so both look alike: a 720 px tall TV is 540 dp, as is the TCL's 1080 px."""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pygame

import arabic
import clockface
import hijri
import prayertimes
import schedule
import weather

PHOTOS = Path(__file__).resolve().parent.parent / "assets" / "photos"
WHITE = (255, 255, 255)

DAYS = ("الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت")
MONTHS = ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر",
          "ديسمبر")
ROW = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")
ROW_NAMES = ("الفجر", "الشروق", "الظهر", "العصر", "المغرب", "العشاء")
RAMADAN = 9

# The rotation by time of day (dawn, day, sunset, night), as in the launcher's Backgrounds.java.
SHRINES = (
    (("shrine_dawn_1.jpg", "العتبة العباسية المقدسة، كربلاء. تصوير Taisir Mahdi (CC BY-SA 4.0)"),
     ("shrine_dawn_2.jpg", "حرم السيدة فاطمة المعصومة، قم. تصوير Amir Pashaei (CC BY-SA 4.0)")),
    (("shrine_day_1.jpg", "حرم الإمام علي، النجف. تصوير Goudarz.memar (CC BY-SA 4.0)"),
     ("shrine_day_2.jpg", "حرم الإمام الرضا، مشهد. khamenei.ir (CC BY 4.0)"),
     ("shrine_day_3.jpg", "حرم السيدة فاطمة المعصومة، قم. تصوير Diego Delso (CC BY-SA 4.0)")),
    (("shrine_sunset_1.jpg", "العتبة العباسية المقدسة، كربلاء. تصوير Taisir Mahdi (CC BY-SA 4.0)"),
     ("shrine_sunset_2.jpg", "حرم الإمام الرضا، مشهد. تصوير Mahdiyar2019 (CC BY-SA 4.0)")),
    (("shrine_night_1.jpg", "حرم الإمام الحسين، كربلاء. تصوير Samerhusseini87 (CC BY-SA 4.0)"),
     ("shrine_night_2.jpg", "حرم الإمام الرضا، مشهد. تصوير mohammad hosein tabatabaeian (CC BY-SA 3.0)"),
     ("shrine_night_3.jpg", "حرم الإمام الرضا، مشهد. تصوير Lstfllw203 (CC BY-SA 4.0)")))


def slot(hours, t):
    """Dawn from Fajr to 45 minutes after sunrise, day until an hour before sunset, sunset until Isha, then night."""
    if t[prayertimes.FAJR] <= hours < t[prayertimes.SUNRISE] + 0.75:
        return 0
    if t[prayertimes.SUNRISE] + 0.75 <= hours < t[prayertimes.SUNSET] - 1:
        return 1
    if t[prayertimes.SUNSET] - 1 <= hours < t[prayertimes.ISHA]:
        return 2
    return 3


def photo(now, cfg):
    """(file, credit) for now: the day number plus the adhans already called today picks from the slot's photos,
    so the photo moves on at every adhan, and the TV shows the same one at the same moment."""
    today = now.date()
    t = prayertimes.compute(today, cfg["latitude"], cfg["longitude"], schedule.zone_hours(today))
    pool = SHRINES[slot(now.hour + now.minute / 60 + now.second / 3600, t)]
    minutes = schedule.prayer_minutes(today, cfg)
    minute = now.hour * 60 + now.minute
    prayers = (schedule.load().get("adhan") or {}).get("prayers") or []
    passed = sum(1 for k in prayers if k in minutes and minutes[k] <= minute)
    step = (today - datetime(1970, 1, 1).date()).days % 100000 + passed
    return pool[step % len(pool)]


def clock12(minute):
    """Minutes after midnight as "4:36" and its ص or م."""
    h, m = divmod(minute % 1440, 60)
    return f"{h % 12 or 12}:{m:02d}", "ص" if h < 12 else "م"


def count(n, one, two, few, many):
    """Arabic counting: one, two, 3 to 10, and 11 up take different forms."""
    if n == 1:
        return one
    if n == 2:
        return two
    return f"{n} {few if n <= 10 else many}"


def until(minutes):
    if minutes <= 0:
        return "حان الآن"
    h, m = divmod(minutes, 60)
    s = "بعد "
    if h:
        s += count(h, "ساعة", "ساعتين", "ساعات", "ساعة")
    if h and m:
        s += " و"
    if m:
        s += count(m, "دقيقة", "دقيقتين", "دقائق", "دقيقة")
    return s


def days(n):
    if n == 1:
        return "يوم واحد"
    if n == 2:
        return "يومان"
    return f"{n} {'أيام' if n <= 10 else 'يوماً'}"


def date_line(date, cfg):
    line = f"{date.day} {MONTHS[date.month - 1]} {date.year}"
    h = hijri.of(date, cfg.get("hijri_offset", 0))
    # The shaper drops the tatweel of "هـ", so the initial form of heh stands in for it.
    return line + (f"، {h[2]} {hijri.MONTHS[h[1] - 1]} {h[0]} ﻫ" if h else "")


def ramadan(date, cfg):
    """(big line, small line) for the Ramadan corner, or None past the calendar's end."""
    offset = cfg.get("hijri_offset", 0)
    h = hijri.of(date, offset)
    if h and h[1] == RAMADAN:
        return f"اليوم {h[2]}", "رمضان كريم"
    for i in range(1, 400):
        d = date + timedelta(days=i)
        h = hijri.of(d, offset)
        if h and h[1] == RAMADAN and h[2] == 1:
            return days(i), f"يبدأ {DAYS[schedule.weekday(d)]} {d.day} {MONTHS[d.month - 1]} تقريباً"
    return None


def next_prayer(now, cfg):
    """(index in ROW, minutes left) of the next prayer, sunrise never counting, tomorrow's Fajr after Isha."""
    minutes = schedule.prayer_minutes(now.date(), cfg)
    elapsed = now.hour * 60 + now.minute + now.second / 60
    for i, k in enumerate(ROW):
        if k != "sunrise" and minutes[k] > elapsed:
            return i, int(-(-(minutes[k] - elapsed) // 1))
    tomorrow = schedule.prayer_minutes(now.date() + timedelta(days=1), cfg)
    return 0, int(-(-(tomorrow["fajr"] + 1440 - elapsed) // 1))


class PhotoFace(clockface.Panels):

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.upright = height > width
        self.u = min(width, height) / 540            # px per dp
        self.s = (width / 720) if self.upright else (height / 720)
        # The fonts the setup steps share with the other face.
        self.big = self._font("bold", 44)
        self.tile = self._font("bold", 37)
        self.note = self._font("medium", 29)
        self.small = self._font("medium", 24)
        s = self.s
        if self.upright:
            self.card = pygame.Rect(round(70 * s), round(150 * s), round(580 * s), round(560 * s))
        else:
            self.card = pygame.Rect(round(40 * s), round(10 * s), round(580 * s), round(560 * s))
        self.fonts = {}
        self.background = None
        self.background_for = None
        self.ramadan = None
        self.ramadan_for = None
        self.drawn = None
        self.photo_for = self.photo = self.weather = None
        self.dx = self.dy = 0

    def font(self, name, sp):
        key = (name, sp)
        if key not in self.fonts:
            file = "playfair.ttf" if name == "playfair" else f"plex_arabic_{name}.ttf"
            self.fonts[key] = pygame.font.Font(str(clockface.FONTS / file), max(8, round(sp * self.u)))
        return self.fonts[key]

    def _background(self, file):
        """The photo cropped to fill the screen, darkened at the top and bottom for the text."""
        if self.background_for == file:
            return self.background
        w, h, u = self.w, self.h, self.u
        back = pygame.Surface((w, h), 0, 32, clockface.MASKS)
        back.fill((0, 0, 0))
        try:
            img = pygame.image.load(str(PHOTOS / file))
            k = max(w / img.get_width(), h / img.get_height())
            img = pygame.transform.smoothscale(img, (round(img.get_width() * k), round(img.get_height() * k)))
            back.blit(img, ((w - img.get_width()) // 2, (h - img.get_height()) // 2))
        except (pygame.error, OSError) as e:
            print("photo:", file, e, flush=True)
        for top, size, alpha in ((True, 200, 0x73), (False, 300 if not self.upright else 420, 0x8C)):
            band = round(size * u)
            shade = pygame.Surface((w, band), pygame.SRCALPHA, 32)
            for y in range(band):
                a = round(alpha * (1 - y / band))
                pygame.draw.line(shade, (0, 0, 0, a), (0, y if top else band - 1 - y), (w, y if top else band - 1 - y))
            back.blit(shade, (0, 0 if top else h - band))
        self.background, self.background_for = back, file
        return back

    def _render(self, text, name, sp, alpha=1.0, shaped=False):
        """White text with the launcher's soft shadow, as one surface."""
        font = self.font(name, sp)
        visual = text if shaped else arabic.visual(text)
        img = font.render(visual, True, WHITE)
        pad = max(2, round(6 * self.u))
        out = pygame.Surface((img.get_width() + 2 * pad, img.get_height() + 2 * pad), pygame.SRCALPHA, 32)
        shadow = font.render(visual, True, (0, 0, 0))
        small = pygame.transform.smoothscale(shadow, (max(1, shadow.get_width() // 4),
                                                      max(1, shadow.get_height() // 4)))
        shadow = pygame.transform.smoothscale(small, shadow.get_size())
        shadow.set_alpha(0x99)
        out.blit(shadow, (pad, pad + max(1, round(self.u))))
        out.blit(img, (pad, pad))
        if alpha < 1:
            out.set_alpha(round(255 * alpha))
        return out, pad

    def _put(self, target, text, name, sp, x, y, align="right", alpha=1.0, shaped=False):
        """Draws text with its top at y and its right edge (or left, or centre) at x; returns its box."""
        img, pad = self._render(text, name, sp, alpha, shaped)
        w, h = img.get_width() - 2 * pad, img.get_height() - 2 * pad
        left = x - w if align == "right" else x - w / 2 if align == "center" else x
        target.blit(img, (round(left - pad + self.dx), round(y - pad + self.dy)))
        return pygame.Rect(round(left), round(y), w, h)

    def _size(self, text, name, sp, shaped=False):
        return self.font(name, sp).size(text if shaped else arabic.visual(text))

    def draw(self, target, now, cfg, playing="", warning="", net=(None, None)):
        kind, info = net
        notes = [t for t in (warning, info if kind == "address" else "") if t]
        note = notes[now.second // 6 % len(notes)] if notes else ""
        minute = now.replace(second=0, microsecond=0)
        if self.photo_for != minute:   # reads the schedule and the weather file, so once a minute
            self.photo_for, self.photo, self.weather = minute, photo(now, cfg), weather.reading()
        (file, credit), w8 = self.photo, self.weather
        key = (minute, playing, note, kind, repr(info) if kind == "setup" else "",
               file, bool(cfg.get("muted")), repr(w8), cfg.get("city"), cfg.get("hijri_offset"),
               cfg.get("latitude"), cfg.get("longitude"), repr(cfg.get("prayer_offsets")))
        if key == self.drawn:
            return   # nothing on this face changes within the minute
        self.drawn = key
        # Every five minutes the text moves a few pixels, so nothing stays on the same pixels for hours.
        rnd = random.Random(int(now.timestamp()) // 300)
        self.dx, self.dy = ((rnd.random() * 2 - 1) * 10 * self.u for _ in range(2))

        target.blit(self._background(file), (0, 0))
        u = self.u
        W, H = self.w / u, self.h / u
        side = 36 if self.upright else 52

        def px(v):
            return v * u

        # Day and dates, top right.
        right = px(W - side)
        top = px(36)
        r = self._put(target, DAYS[schedule.weekday(now.date())], "bold", 34, right, top)
        self._put(target, date_line(now.date(), cfg), "regular", 15, right, r.bottom + px(6), alpha=0.9)

        # Weather, top left, only once there is a reading.
        if w8:
            lines = [(cfg.get("city", ""), "regular", 13, 0.85),
                     (f"العظمى {w8['max']}° والصغرى {w8['min']}°", "regular", 13, 0.85)]
            cond = weather.describe(w8["code"])
            temp = f"{w8['temp']}°"
            tw, th = self._size(temp, "medium", 32)
            cw = self._size(cond, "regular", 16)[0]
            width = max(self._size(lines[0][0], "regular", 13)[0], self._size(lines[1][0], "regular", 13)[0],
                        tw + px(8) + cw)
            x = px(side) + width
            r = self._put(target, lines[0][0], "regular", 13, x, top, alpha=0.85)
            r = self._put(target, temp, "medium", 32, x, r.bottom)
            self._put(target, cond, "regular", 16, x - tw - px(8), r.bottom - self._size(cond, "regular", 16)[1]
                      - px(4))
            self._put(target, lines[1][0], "regular", 13, x, r.bottom, alpha=0.85)

        # The time, with ص/م on its left.
        hm, ampm = clock12(now.hour * 60 + now.minute)
        big = self.font("playfair", 150)
        tw, th = big.size(hm)
        center = px(300) if self.upright else px((36 + (H - 30 - 60)) / 2)
        r = self._put(target, hm, "playfair", 150, right, center - th / 2, shaped=True)
        baseline = r.top + big.get_ascent()
        ah = self.font("regular", 26).get_ascent()
        self._put(target, ampm, "regular", 26, r.left - px(12), baseline - ah - px(4))

        if note:
            y = r.bottom + px(10) if self.upright else px(126)
            color_note = clockface.WARN if note == warning else (200, 240, 200)
            self._note(target, note, color_note, self.w / 2, y)

        # The next prayer over the day's times, bottom right.
        nxt, left = next_prayer(now, cfg)
        minutes = schedule.prayer_minutes(now.date(), cfg)
        cells = self._cells(minutes)
        cw = max(c[2] for c in cells)
        ch = cells[0][3]
        gap = px(4)
        bottom = px(H - 30 - 22)
        per_row = 3 if self.upright else 6
        rows = (len(ROW) + per_row - 1) // per_row
        grid_top = bottom - rows * ch - (rows - 1) * gap
        for i, (name, (t, ap), _, _) in enumerate(cells):
            col, row = i % per_row, i // per_row
            box = pygame.Rect(round(right - (col + 1) * cw - col * gap), round(grid_top + row * (ch + gap)),
                              round(cw), round(ch))
            on = i == nxt
            if on:
                glass = pygame.Surface(box.size, pygame.SRCALPHA, 32)
                radius = round(12 * u)
                pygame.draw.rect(glass, (255, 255, 255, 0x38), glass.get_rect(), border_radius=radius)
                pygame.draw.rect(glass, (255, 255, 255, 0x66), glass.get_rect(), max(1, round(u / 2)),
                                 border_radius=radius)
                target.blit(glass, (box.x + self.dx, box.y + self.dy))
            alpha = 1 if on else 0.72
            inner = box.right - px(14)
            nr = self._put(target, name, "regular", 13, inner, box.top + px(8), alpha=alpha)
            self._put(target, t + " " + arabic.shape(ap), "medium", 18, inner, nr.bottom, alpha=alpha, shaped=True)

        label = "الصلاة القادمة" if not playing else "يُشغَّل الآن: " + playing
        y = grid_top - px(10)
        ph = self._size(ROW_NAMES[nxt], "bold", 30)[1]
        pr = self._put(target, ROW_NAMES[nxt], "bold", 30, right - px(14), y - ph)
        ir = self._put(target, until(left), "medium", 18, pr.left - px(20),
                       pr.bottom - self._size("بعد", "medium", 18)[1] - px(3))
        lh = self._size(label, "regular", 12)[1]
        self._put(target, label, "regular", 12, right - px(14), pr.top - lh + px(4), alpha=0.8)
        if cfg.get("muted"):
            self._mute_icon(target, ir.left - px(40) + self.dx, ir.centery + self.dy)

        # Ramadan, bottom left; upright it sits under the time, where the left side is free.
        if self.ramadan_for != now.date():
            self.ramadan_for, self.ramadan = now.date(), ramadan(now.date(), cfg)
        if self.ramadan:
            big_line, sub = self.ramadan
            sizes = [self._size("رمضان", "regular", 12), self._size(big_line, "bold", 26),
                     self._size(sub, "regular", 13)]
            width = max(s[0] for s in sizes)
            x = px(side) + width
            y = (px(H - 30 - 26) - sum(s[1] for s in sizes)) if not self.upright else pr.top - px(150)
            r = self._put(target, "رمضان", "regular", 12, x, y, alpha=0.8)
            r = self._put(target, big_line, "bold", 26, x, r.bottom)
            self._put(target, sub, "regular", 13, x, r.bottom, alpha=0.9)

        # The photo's credit, bottom left (the photos are CC BY and BY-SA).
        ch_credit = self._size(credit, "regular", 9)[1]
        self._put(target, credit, "regular", 9, px(side), px(H - 30) - ch_credit, align="left", alpha=0.65)

        if kind == "setup":
            self._setup(target, info)

    def _cells(self, minutes):
        """(name, (time, ص/م), width, height) for each of the six times, in dp-scaled px."""
        u = self.u
        out = []
        for k, name in zip(ROW, ROW_NAMES):
            t = clock12(minutes[k])
            nw, nh = self._size(name, "regular", 13)
            tw, th = self._size(t[0] + " " + arabic.shape(t[1]), "medium", 18, shaped=True)
            out.append((name, t, max(nw, tw) + 28 * u, nh + th + 16 * u))
        return out

    def _note(self, target, text, color, x, y):
        """A warning or the address, on a dark band so it reads over any photo."""
        font = self.font("medium", 16)
        img = font.render(arabic.visual(text), True, color)
        band = pygame.Surface((img.get_width() + round(24 * self.u), img.get_height() + round(8 * self.u)),
                              pygame.SRCALPHA, 32)
        pygame.draw.rect(band, (0, 0, 0, 0xA0), band.get_rect(), border_radius=round(10 * self.u))
        band.blit(img, img.get_rect(center=band.get_rect().center))
        target.blit(band, band.get_rect(midtop=(round(x + self.dx), round(y + self.dy))))
