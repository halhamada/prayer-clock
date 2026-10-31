"""Draws the clock screen: the dates, the analog clock on its card, four prayer tiles and the countdown to the next
one. Upright like the wall clock it copies, or in two columns on a landscape screen. Everything that does not change
each second is drawn once into a cached background."""

import math
from datetime import datetime, timedelta
from pathlib import Path

import pygame
import pygame.gfxdraw

import arabic
import hijri
import schedule

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
MASKS = (0xFF0000, 0x00FF00, 0x0000FF, 0)

NAVY_TOP, NAVY_BOTTOM = (10, 20, 72), (3, 8, 40)
BOKEH = (60, 110, 200)
FRAME = (28, 96, 70)
GREEN_TEXT = (196, 245, 190)
CARD, CARD_EDGE = (178, 235, 232), (232, 138, 122)
INK = (20, 20, 22)
HAND = (120, 160, 240)
CENTER = (232, 188, 48)
PURPLE = (124, 58, 237)
TILE_LINE = (205, 225, 240)
TILE_BG, TILE_NEXT = (6, 8, 20), (8, 122, 30)
TIME_BLUE = (190, 225, 255)
NAME_YELLOW = (250, 225, 60)
LABEL_BLUE = (180, 215, 255)
PINK = (250, 120, 160)
COUNT_BG = (10, 10, 12)
COUNT_YELLOW = (240, 205, 60)
WARN = (255, 140, 120)

TILES = (("fajr", "فجر"), ("dhuhr", "ظهر"), ("sunrise", "شروق"), ("maghrib", "مغرب"))
NEXT_LABELS = {"fajr": "المتبقي للفجر", "sunrise": "المتبقي للشروق", "dhuhr": "المتبقي للظهر",
               "maghrib": "المتبقي للمغرب"}
AR_DAYS = ("الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت")
EN_DAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
EN_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def next_prayer(now, cfg):
    """(key, seconds left) of the next prayer on the tiles, tomorrow's Fajr once they have all passed."""
    today = schedule.prayer_minutes(now.date(), cfg)
    midnight = datetime(now.year, now.month, now.day)
    elapsed = (now - midnight).total_seconds()
    for key in ("fajr", "sunrise", "dhuhr", "maghrib"):
        if today[key] * 60 > elapsed:
            return key, int(today[key] * 60 - elapsed)
    tomorrow = schedule.prayer_minutes(now.date() + timedelta(days=1), cfg)
    return "fajr", int(tomorrow["fajr"] * 60 + 86400 - elapsed)


def h12(minute):
    return f"{(minute // 60) % 12 or 12}:{minute % 60:02d}"


def hijri_line(date, cfg):
    h = hijri.of(date, cfg.get("hijri_offset", 0))
    day = AR_DAYS[schedule.weekday(date)]
    return f"{day}، {h[2]} {hijri.MONTHS[h[1] - 1]} {h[0]}" if h else day


def gregorian_line(date):
    return f"{EN_DAYS[schedule.weekday(date)]}, {EN_MONTHS[date.month - 1]} {date.day}, {date.year}"


class Face:

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.upright = height >= width
        self.s = (width / 720) if self.upright else (height / 720)
        s = self.s
        self.big = self._font("bold", 44)
        self.tile = self._font("bold", 37)
        self.label = self._font("bold", 38)
        self.digital = self._font("bold", 36)
        self.count = self._font("bold", 66)
        self.small = self._font("medium", 24)
        if self.upright:
            self.hijri_y, self.greg_y = 68 * s, 150 * s
            self.date_x = width / 2
            self.card = pygame.Rect(0, 0, round(580 * s), round(590 * s))
            self.card.midtop = (width // 2, round(198 * s))
            self.label_y = 1056 * s
            self.count_box = pygame.Rect(0, 0, round(420 * s), round(100 * s))
            self.count_box.midtop = (width // 2, round(1120 * s))
            x1, x2, w = 366 * s, 104 * s, 250 * s
            ys = (806 * s, 900 * s)
        else:
            self.card = pygame.Rect(round(40 * s), round(50 * s), round(620 * s), round(620 * s))
            col = pygame.Rect(self.card.right + round(40 * s), 0, width - self.card.right - round(80 * s), height)
            self.date_x = col.centerx
            self.hijri_y, self.greg_y = 92 * s, 164 * s
            self.label_y = 470 * s
            self.count_box = pygame.Rect(0, 0, round(420 * s), round(100 * s))
            self.count_box.midtop = (col.centerx, round(530 * s))
            w = 250 * s
            x1, x2 = col.centerx + 8 * s, col.centerx - 8 * s - w
            ys = (230 * s, 324 * s)
        self.tiles = {}
        for i, (key, name) in enumerate(TILES):
            r = pygame.Rect(round(x1 if i < 2 else x2), round(ys[i % 2]), round(w), round(76 * s))
            self.tiles[key] = (r, name)
        self.back_key = None
        self.back = None
        self.face = self._clock_card()
        self.backdrop = self._backdrop()

    def _font(self, weight, size):
        return pygame.font.Font(str(FONTS / f"plex_arabic_{weight}.ttf"), max(8, round(size * self.s)))

    def _text(self, target, font, text, color, center=None, right=None, left=None):
        img = font.render(arabic.visual(text), True, color)
        r = img.get_rect()
        if center:
            r.center = center
        if right:
            r.midright = right
        if left:
            r.midleft = left
        target.blit(img, r)
        return r

    def _surface(self, size):
        return pygame.Surface(size, 0, 32, MASKS)

    def _backdrop(self):
        """Night-blue gradient with soft out-of-focus lights and a thin frame."""
        w, h = self.w, self.h
        back = self._surface((w, h))
        for y in range(h):
            t = y / max(1, h - 1)
            color = tuple(round(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM))
            pygame.draw.line(back, color, (0, y), (w, y))
        small = pygame.Surface((max(1, w // 8), max(1, h // 8)), pygame.SRCALPHA, 32)
        lights = ((0.16, 0.16, 16, 14), (0.84, 0.3, 22, 10), (0.1, 0.58, 14, 12), (0.9, 0.7, 20, 12),
                  (0.22, 0.86, 20, 13), (0.76, 0.93, 16, 10), (0.52, 0.04, 14, 9))
        for fx, fy, r, a in lights:
            spot = pygame.Surface(small.get_size(), pygame.SRCALPHA, 32)
            center = (round(small.get_width() * fx), round(small.get_height() * fy))
            for k in range(12, 0, -1):
                pygame.draw.circle(spot, BOKEH + (a * (13 - k),), center, max(1, round(r * self.s * k / 12)))
            small.blit(spot, (0, 0))
        back.blit(pygame.transform.smoothscale(small, (w, h)), (0, 0))
        m = round(10 * self.s)
        pygame.draw.rect(back, FRAME, (m, m, w - 2 * m, h - 2 * m), max(1, round(3 * self.s)))
        return back

    def _clock_card(self):
        """The card with its dial, drawn at twice the size and scaled down so the edges come out smooth."""
        w, h = self.card.size
        k = 2
        big = pygame.Surface((w * k, h * k), pygame.SRCALPHA, 32)
        edge = max(2, round(5 * self.s)) * k
        radius = round(12 * self.s) * k
        pygame.draw.rect(big, CARD, big.get_rect(), border_radius=radius)
        pygame.draw.rect(big, CARD_EDGE, big.get_rect(), edge, border_radius=radius)
        cx, cy = w * k / 2, h * k / 2
        r = min(w, h) * k * 0.46
        for i in range(60):
            a = math.radians(i * 6)
            x, y = cx + r * math.sin(a), cy - r * math.cos(a)
            dot = (3.4 if i % 5 == 0 else 2.2) * self.s * k
            pygame.draw.circle(big, INK, (x, y), dot)
        num = pygame.font.Font(str(FONTS / "plex_arabic_medium.ttf"), round(66 * self.s) * k)
        for n in range(1, 13):
            a = math.radians(n * 30)
            img = num.render(str(n), True, INK)
            big.blit(img, img.get_rect(center=(cx + r * 0.83 * math.sin(a), cy - r * 0.83 * math.cos(a))))
        return pygame.transform.smoothscale(big, (w, h))

    def _hand(self, target, center, angle, length, width, tail=0):
        a = math.radians(angle)
        sx, cy = math.sin(a), math.cos(a)
        px, py = cy * width / 2, sx * width / 2
        tip_x, tip_y = center[0] + sx * length, center[1] - cy * length
        back_x, back_y = center[0] - sx * tail, center[1] + cy * tail
        points = [(back_x - px, back_y - py), (tip_x - px * 0.5, tip_y - py * 0.5),
                  (tip_x + px * 0.5, tip_y + py * 0.5), (back_x + px, back_y + py)]
        points = [(round(x), round(y)) for x, y in points]
        pygame.gfxdraw.filled_polygon(target, points, HAND)
        pygame.gfxdraw.aapolygon(target, points, HAND)

    def _static(self, now, cfg, highlight):
        """The parts that change at most a few times a day."""
        key = (now.date(), highlight, cfg.get("hijri_offset"), cfg.get("latitude"), cfg.get("longitude"),
               repr(cfg.get("prayer_offsets")))
        if key == self.back_key:
            return self.back
        back = self.backdrop.copy()
        self._text(back, self.big, hijri_line(now.date(), cfg), GREEN_TEXT, center=(self.date_x, self.hijri_y))
        self._text(back, self.big, gregorian_line(now.date()), GREEN_TEXT, center=(self.date_x, self.greg_y))
        back.blit(self.face, self.card)
        minutes = schedule.prayer_minutes(now.date(), cfg)
        s = self.s
        for k, (r, name) in self.tiles.items():
            pygame.draw.rect(back, TILE_NEXT if k == highlight else TILE_BG, r, border_radius=round(12 * s))
            pygame.draw.rect(back, TILE_LINE, r, max(1, round(2 * s)), border_radius=round(12 * s))
            self._text(back, self.tile, name, NAME_YELLOW, right=(r.right - round(20 * s), r.centery))
            self._text(back, self.tile, h12(minutes[k]), TIME_BLUE, left=(r.left + round(20 * s), r.centery))
        b = self.count_box
        pygame.draw.rect(back, COUNT_BG, b, border_radius=round(14 * s))
        pygame.draw.rect(back, TILE_LINE, b, max(1, round(3 * s)), border_radius=round(14 * s))
        self.back, self.back_key = back, key
        return back

    def draw(self, target, now, cfg, playing="", warning=""):
        key, left = next_prayer(now, cfg)
        target.blit(self._static(now, cfg, key), (0, 0))
        s = self.s
        c = self.card.center
        r = min(self.card.size) * 0.46

        sec = now.second
        minute = now.minute + sec / 60
        hour = (now.hour % 12) + minute / 60
        self._text(target, self.digital, f"{now.hour % 12 or 12} : {now.minute:02d} : {sec:02d}", PURPLE,
                   center=(c[0], c[1] + 112 * s))
        self._hand(target, c, hour * 30, r * 0.55, 20 * s)
        self._hand(target, c, minute * 6, r * 0.93, 7 * s)
        self._hand(target, c, sec * 6, r * 0.93, 7 * s)
        radius = round(33 * s)
        pygame.gfxdraw.filled_circle(target, c[0], c[1], radius, CENTER)
        pygame.gfxdraw.aacircle(target, c[0], c[1], radius, CENTER)

        y = self.label_y
        if playing:
            self._text(target, self.label, playing, GREEN_TEXT, center=(self.date_x, y))
        else:
            r_text = self._text(target, self.label, NEXT_LABELS[key], LABEL_BLUE,
                                center=(self.date_x + 20 * s, y))
            x = r_text.left - 24 * s
            pygame.draw.polygon(target, PINK, ((x - 18 * s, y - 9 * s), (x + 18 * s, y - 9 * s), (x, y + 9 * s)))

        h, m, sc = left // 3600, left % 3600 // 60, left % 60
        img = self.count.render(f"{h:02d} : {m:02d} : {sc:02d}", True, COUNT_YELLOW)
        target.blit(img, img.get_rect(center=self.count_box.center))
        if warning:
            self._text(target, self.small, warning, WARN, center=(self.date_x, self.h - 28 * s))
