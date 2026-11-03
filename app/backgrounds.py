"""The photo face's photos, by time of day (dawn, day, sunset, night), as in the MITV launcher's Backgrounds.java.
By default they rotate through photos of the shrines, moving on at every adhan. The dashboard can switch to manual:
then its uploads are used, in the data dir's backgrounds folder named by slot, or "all" for every time, a slot's own
photo winning over "all", and the bundled landscapes otherwise. Uploads are turned upright from their EXIF
orientation and scaled down to screen size once, when they arrive, so the device never decodes a phone photo
twice."""

import os
from datetime import date
from pathlib import Path

import pygame

import prayertimes
import schedule
import settings

PHOTOS = Path(__file__).resolve().parent.parent / "assets" / "photos"
SLOTS = ("dawn", "day", "sunset", "night")
ALL = "all"
MAX_SIDE = 1920

DEFAULTS = (("saver_dawn.jpg", "نخيل عند الشروق. تصوير Ahmed Aymen Amin Hasan (CC BY-SA 4.0)"),
            ("saver_day.jpg", "الربع الخالي. تصوير Krzysztof Ziarnek, Kenraiz (CC BY-SA 4.0)"),
            ("saver_sunset.jpg", "غروب في الصحراء. تصوير Farhan Riaz (CC BY-SA 4.0)"),
            ("saver_night.jpg", "درب التبانة فوق صحراء أتاكاما، تشيلي. تصوير G. Hüdepohl/ESO (CC BY 4.0)"))

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


def folder():
    return settings.DATA / "backgrounds"


def own(slot):
    """The uploaded photo for slot, or None."""
    path = folder() / f"{slot}.jpg"
    return path if path.is_file() else None


def is_slot(slot):
    return slot == ALL or slot in SLOTS


def slot_of(hours, t):
    """Dawn from Fajr to 45 minutes after sunrise, day until an hour before sunset, sunset until Isha, then night."""
    if t[prayertimes.FAJR] <= hours < t[prayertimes.SUNRISE] + 0.75:
        return 0
    if t[prayertimes.SUNRISE] + 0.75 <= hours < t[prayertimes.SUNSET] - 1:
        return 1
    if t[prayertimes.SUNSET] - 1 <= hours < t[prayertimes.ISHA]:
        return 2
    return 3


def pick(now, cfg):
    """(path, credit) of the photo to show now."""
    today = now.date()
    t = prayertimes.compute(today, cfg["latitude"], cfg["longitude"], schedule.zone_hours(today))
    i = slot_of(now.hour + now.minute / 60 + now.second / 3600, t)
    if cfg.get("photo_rotate", True):
        pool = SHRINES[i]
        file, credit = pool[_step(now, cfg) % len(pool)]
        return PHOTOS / file, credit
    mine = own(SLOTS[i]) or own(ALL)
    if mine:
        return mine, ""
    file, credit = DEFAULTS[i]
    return PHOTOS / file, credit


def _step(now, cfg):
    """The day number plus the adhans already called today, so the photo moves on at every adhan and the TV shows
    the same one at the same moment. Worked out from the clock, so it stays right across reboots."""
    today = now.date()
    minutes = schedule.prayer_minutes(today, cfg)
    minute = now.hour * 60 + now.minute
    prayers = (schedule.load().get("adhan") or {}).get("prayers") or []
    passed = sum(1 for k in prayers if k in minutes and minutes[k] <= minute)
    return (today - date(1970, 1, 1)).days % 100000 + passed


def shown(slot):
    """The file the dashboard previews for slot: the upload, or the bundled photo it falls back to."""
    mine = own(slot)
    if mine or slot == ALL:
        return mine
    return own(ALL) or PHOTOS / DEFAULTS[SLOTS.index(slot)][0]


def status(cfg):
    return {"rotate": bool(cfg.get("photo_rotate", True)), **{s: own(s) is not None for s in (ALL,) + SLOTS}}


def save(slot, upload):
    """Turns the uploaded file into slot's photo; False if it is not an image pygame can read."""
    try:
        img = pygame.image.load(str(upload))
    except (pygame.error, OSError):
        return False
    turn = {3: 180, 6: -90, 8: 90}.get(orientation(upload))
    if turn:
        img = pygame.transform.rotate(img, turn)
    w, h = img.get_size()
    flat = pygame.Surface((w, h), 0, 32)   # smoothscale and JPEG need plain 32-bit colour, whatever came in
    flat.fill((0, 0, 0))
    flat.blit(img, (0, 0))
    k = MAX_SIDE / max(w, h)
    img = pygame.transform.smoothscale(flat, (round(w * k), round(h * k))) if k < 1 else flat
    folder().mkdir(parents=True, exist_ok=True)
    tmp = folder() / f"{slot}.new.jpg"
    pygame.image.save(img, str(tmp))
    os.replace(tmp, folder() / f"{slot}.jpg")
    return True


def delete(slot):
    mine = own(slot)
    if mine:
        mine.unlink()


def orientation(path):
    """The EXIF orientation of a JPEG (1 upright, 3 upside down, 6 and 8 on its side), 1 if it has none."""
    try:
        with open(path, "rb") as f:
            data = f.read(256 * 1024)
    except OSError:
        return 1
    if data[:2] != b"\xff\xd8":
        return 1
    i = 2
    while i + 4 <= len(data) and data[i] == 0xFF:
        marker, size = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\0\0":
            tiff = data[i + 10:i + 2 + size]
            order = "little" if tiff[:2] == b"II" else "big"
            ifd = int.from_bytes(tiff[4:8], order)
            for k in range(int.from_bytes(tiff[ifd:ifd + 2], order)):
                e = ifd + 2 + 12 * k
                if int.from_bytes(tiff[e:e + 2], order) == 0x0112:
                    return int.from_bytes(tiff[e + 8:e + 10], order)
            return 1
        if marker in (0xDA, 0xD9):   # the image data starts: no EXIF before it
            return 1
        i += 2 + size
    return 1
