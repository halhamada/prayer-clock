"""The prayer clock: draws the screen once a second, plays the schedule, and serves the dashboard.

Run with no arguments on the device. --preview FILE draws one frame to a PNG instead, for checking the look on any
computer: --at 2026-01-30T12:52:05 --size 720x1280."""

import argparse
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import clockface
import network
import output
import photoface
import player
import schedule
import server
import settings
import weather

BOOT_GRACE_SECONDS = 180


class Clock:
    """Whether the system time can be trusted. A Pi has no battery clock: it boots on the last saved time, and only
    jumps to the right one once it reaches a time server, so nothing plays until then. After three minutes it plays
    regardless, because a house without internet still needs its adhan."""

    def __init__(self):
        self.set_by_hand = False

    def synced(self):
        return (os.name != "posix" or self.set_by_hand or Path("/dev/rtc0").exists()
                or Path("/run/systemd/timesync/synchronized").exists())

    def usable(self):
        return self.synced() or _uptime() > BOOT_GRACE_SECONDS

    def set(self, epoch):
        self.set_by_hand = server.set_system_time(epoch)
        return self.set_by_hand


class App:

    def __init__(self):
        self.player = player.Player()
        self.clock = Clock()
        self.auth = server.Auth()
        self.network = network.Manager()


def _uptime():
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except OSError:
        return 1e9


def make_face(cfg, width, height):
    """The face the dashboard picked: the mosque wall clock, or the photo screen of the TVs."""
    return (photoface.PhotoFace if cfg.get("face") == "photo" else clockface.Face)(width, height)


def wait_for_framebuffer():
    while True:
        info = output.probe()
        if info and os.path.exists(output.DEVICE):
            return info
        print("waiting for the display", flush=True)
        time.sleep(1)


def run():
    pygame.font.init()
    app = App()
    app.network.start()
    server.start(app)
    print("dashboard on port", server.PORT, flush=True)
    screen = output.Framebuffer(*wait_for_framebuffer())
    scheduler = schedule.Scheduler(app.player)
    face = surface = size = None
    last_minute = None
    while True:
        now = datetime.now()
        cfg = settings.load()
        wanted = (screen.logical_size(cfg["rotate"]), cfg.get("face"))
        if wanted != size:
            size = wanted
            face = make_face(cfg, *size[0])
            surface = output.logical_surface(size[0])

        minute = now.replace(second=0, microsecond=0)
        if minute != last_minute:
            if cfg.get("face") == "photo":
                weather.refresh(cfg["latitude"], cfg["longitude"])
            if app.clock.usable():
                last_minute = minute
                try:
                    scheduler.tick(now, cfg)
                except Exception as e:   # a bad schedule must not take the clock down with it
                    print("schedule error:", repr(e), flush=True)

        warning = "" if app.clock.synced() else "الوقت غير مؤكد: وصّل الجهاز بالإنترنت أو اضبطه من اللوحة"
        face.draw(surface, now, cfg, app.player.title(), warning, app.network.screen())
        screen.show(surface, cfg["rotate"])
        time.sleep(max(0.05, 1.02 - time.time() % 1))


def preview(path, at, size, setup=False):
    pygame.font.init()
    w, h = (int(v) for v in size.split("x"))
    surface = output.logical_surface((w, h))
    now = datetime.fromisoformat(at) if at else datetime.now()
    net = (None, None)
    if setup:
        net = ("setup", {"mode": "hotspot", "ssid": "", "error": "", "hotspot": {
            "ssid": network.HOTSPOT_SSID, "password": "48275936", "address": network.HOTSPOT_ADDRESS}})
    make_face(settings.load(), w, h).draw(surface, now, settings.load(), net=net)
    pygame.image.save(surface, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview")
    parser.add_argument("--at")
    parser.add_argument("--size", default="720x1280")
    parser.add_argument("--setup", action="store_true", help="draw the network setup steps")
    args = parser.parse_args()
    if args.preview:
        preview(args.preview, args.at, args.size, args.setup)
    else:
        run()


if __name__ == "__main__":
    sys.exit(main())
