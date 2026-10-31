"""Plays one audio file at a time through mpg123, which needs a fraction of the CPU any fuller player does."""

import re
import subprocess
import threading

import settings

FULL_SCALE = 32768


def command(path, cfg):
    scale = FULL_SCALE * max(0, min(100, int(cfg.get("volume", 100)))) // 100
    cmd = ["mpg123", "-q", "-f", str(scale)]
    if cfg.get("audio_device"):
        cmd += ["-o", "alsa", "-a", cfg["audio_device"]]
    return cmd + [str(path)]


def devices():
    """The sound cards ALSA offers as (name, label), for the dashboard's picker."""
    try:
        out = subprocess.run(["aplay", "-L"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    found = []
    for name in re.findall(r"^default:CARD=\S+", out, re.M):
        card = name.split("=", 1)[1]
        label = {"vc4hdmi": "HDMI (التلفزيون)", "Headphones": "مخرج السماعات 3.5 ملم"}.get(card, card)
        found.append((name, label))
    return found


class Player:

    def __init__(self):
        self._lock = threading.Lock()
        self._proc = None
        self._title = ""

    def play(self, path, title):
        """Starts path, cutting off whatever was playing."""
        with self._lock:
            self._stop()
            print("playing:", title, path, flush=True)
            try:
                self._proc = subprocess.Popen(command(path, settings.load()), stdin=subprocess.DEVNULL)
                self._title = title
            except OSError as e:
                print("could not start mpg123:", e, flush=True)

    def stop(self):
        with self._lock:
            self._stop()

    def is_playing(self):
        with self._lock:
            return self._running()

    def title(self):
        """What is playing now, or an empty string."""
        with self._lock:
            return self._title if self._running() else ""

    def _running(self):
        return self._proc is not None and self._proc.poll() is None

    def _stop(self):
        if self._running():
            self._proc.terminate()
            try:
                self._proc.wait(2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._proc = None
