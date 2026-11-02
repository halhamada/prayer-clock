"""Wi-Fi through NetworkManager (nmcli), and a setup hotspot for when the device finds no network it knows, as after
moving it to another house. The phone joins the hotspot, opens the dashboard at 10.42.0.1:8080 and picks the new
network; the screen shows the steps, and the new address once it is connected.

Without nmcli (another OS, or a computer used for development) all of this stays off."""

import os
import secrets
import shutil
import subprocess
import threading
import time

import settings

HOTSPOT = "PrayerClock-Setup"      # NetworkManager's name for the hotspot connection
HOTSPOT_SSID = "PrayerClock"
HOTSPOT_ADDRESS = "10.42.0.1"      # what NetworkManager gives itself on a shared connection
OFFLINE_WAIT = 90       # after a power cut the router can take this long to come back
HOTSPOT_MIN = 300       # hotspot time before trying the saved networks again
RETRY_WAIT = 45         # how long such a try gets before the hotspot comes back
IDLE = 180              # a phone on the setup page within this long keeps the hotspot up
SHOW_SETUP = 600        # the steps cover the clock face this long after the hotspot starts or is used
SHOW_ADDRESS = 600      # the new address stays on screen this long after connecting


def split(line):
    """One line of nmcli -t output: fields split on ':', with nmcli's '\\:' escapes undone."""
    fields, cur, i = [], "", 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            cur += line[i + 1]
            i += 2
            continue
        if line[i] == ":":
            fields.append(cur)
            cur = ""
        else:
            cur += line[i]
        i += 1
    return fields + [cur]


def nmcli(*args, timeout=20):
    try:
        r = subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr or r.stdout).strip()


def reason(message):
    """nmcli's error as something to show the user."""
    m = message.lower()
    if "secrets were required" in m or "802-1x" in m or "psk" in m or "password" in m:
        return "كلمة المرور غير صحيحة"
    if "no network with ssid" in m:
        return "الشبكة غير موجودة أو بعيدة"
    return "تعذر الاتصال بالشبكة"


class Manager:

    def __init__(self):
        self.enabled = os.name == "posix" and shutil.which("nmcli") is not None
        self.lock = threading.Lock()
        self.mode = "starting"        # connected, offline, hotspot, connecting
        self.ssid = ""                # the network in use, or being joined
        self.address = ""
        self.error = ""
        self.networks = []            # last scan, kept for while the radio is busy being a hotspot
        self.wifi = ""                # the Wi-Fi interface, like wlan0
        self.offline_since = time.monotonic()
        self.hotspot_since = 0
        self.seen = 0                 # last dashboard request through the hotspot
        self.shown_address = ""
        self.address_until = 0
        self.joining = False

    def start(self):
        if self.enabled:
            threading.Thread(target=self._loop, name="network", daemon=True).start()
        return self

    def touch(self):
        self.seen = time.monotonic()

    def password(self):
        cfg = settings.load()
        if not cfg.get("hotspot_password"):
            cfg = settings.save({"hotspot_password": "".join(secrets.choice("23456789") for _ in range(8))})
        return cfg["hotspot_password"]

    def status(self):
        with self.lock:
            s = {"enabled": self.enabled, "mode": self.mode, "ssid": self.ssid, "address": self.address,
                 "error": self.error}
        if self.enabled:
            s["hotspot"] = {"ssid": HOTSPOT_SSID, "password": self.password(), "address": HOTSPOT_ADDRESS}
        return s

    def screen(self):
        """What the clock face shows about the network: ("setup", status) to cover the dial with the steps,
        ("address", text) for a line at the bottom, or (None, None)."""
        now = time.monotonic()
        s = self.status()
        if s["mode"] in ("hotspot", "connecting") and (now - self.hotspot_since < SHOW_SETUP
                                                     or now - self.seen < SHOW_SETUP):
            return "setup", s
        if s["mode"] == "hotspot":
            return "address", f"للإعداد: اتصل بشبكة {HOTSPOT_SSID} وافتح {HOTSPOT_ADDRESS}:8080"
        if s["mode"] == "connected" and now < self.address_until:
            return "address", f"للتحكم من الجوال: {s['address']}:8080"
        return None, None

    # The loop

    def _loop(self):
        while True:
            try:
                self._step()
            except Exception as e:   # never let the network take the clock down
                print("network error:", repr(e), flush=True)
            time.sleep(5)

    def _step(self):
        if self.joining:
            return
        now = time.monotonic()
        link = self._link()
        hotspot = self._hotspot_active()
        if link:
            if hotspot:
                self._hotspot_down()
            name, address = link
            with self.lock:
                self.mode, self.ssid, self.address, self.error = "connected", name, address, ""
            if address != self.shown_address:
                self.shown_address = address
                self.address_until = now + SHOW_ADDRESS
                print("network:", name, address, flush=True)
            self.offline_since = None
            return
        if hotspot:
            with self.lock:
                self.mode, self.address = "hotspot", HOTSPOT_ADDRESS
            # Now and then let NetworkManager look for a saved network, in case the router was only slow to boot,
            # but not while someone is on the setup page.
            if (self._saved_wifi() and now - self.hotspot_since > HOTSPOT_MIN and now - self.seen > IDLE):
                print("network: trying the saved networks", flush=True)
                self._hotspot_down()
                self.offline_since = now - OFFLINE_WAIT + RETRY_WAIT
            return
        with self.lock:
            self.mode, self.ssid, self.address = "offline", "", ""
        if self.offline_since is None:
            self.offline_since = now
        if now - self.offline_since > OFFLINE_WAIT and self.wifi_device():
            self._hotspot_up()

    # NetworkManager

    def wifi_device(self):
        if not self.wifi:
            ok, out = nmcli("-t", "-f", "DEVICE,TYPE", "device")
            for line in out.splitlines() if ok else []:
                f = split(line)
                if len(f) >= 2 and f[1] == "wifi":
                    self.wifi = f[0]
                    break
        return self.wifi

    def _link(self):
        """(name, address) of the connection in use, wired or Wi-Fi but not the hotspot; None if there is none."""
        ok, out = nmcli("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device")
        for line in out.splitlines() if ok else []:
            f = split(line)
            if len(f) < 4 or f[1] not in ("wifi", "ethernet") or f[2] != "connected" or f[3] == HOTSPOT:
                continue
            ok, ip = nmcli("-g", "IP4.ADDRESS", "device", "show", f[0])
            address = ip.split("|")[0].split("/")[0].strip() if ok else ""
            if address:
                return ("سلكي" if f[1] == "ethernet" else f[3]), address
        return None

    def _hotspot_active(self):
        ok, out = nmcli("-t", "-f", "NAME", "connection", "show", "--active")
        return ok and HOTSPOT in out.splitlines()

    def _saved_wifi(self):
        ok, out = nmcli("-t", "-f", "NAME,TYPE", "connection", "show")
        return ok and any(f[0] != HOTSPOT and f[1:2] == ["802-11-wireless"] for f in map(split, out.splitlines()))

    def scan(self, rescan=True):
        """Networks in reach as [{"ssid", "signal", "secure"}], strongest first. The radio cannot scan while it is
        the hotspot, so then this is the list from just before."""
        if self.mode == "hotspot" or not self.wifi_device():
            return self.networks
        ok, out = nmcli("-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", self.wifi,
                        "--rescan", "yes" if rescan else "no", timeout=30)
        best = {}
        for line in out.splitlines() if ok else []:
            f = split(line)
            if len(f) < 3 or not f[0]:
                continue
            signal = int(f[1]) if f[1].isdigit() else 0
            if f[0] not in best or best[f[0]]["signal"] < signal:
                best[f[0]] = {"ssid": f[0], "signal": signal, "secure": f[2] not in ("", "--")}
        self.networks = sorted(best.values(), key=lambda n: -n["signal"])
        return self.networks

    def _hotspot_up(self):
        self.scan()
        ok, out = nmcli("-t", "-f", "NAME", "connection", "show")
        if HOTSPOT not in out.splitlines():
            ok, out = nmcli("connection", "add", "type", "wifi", "ifname", self.wifi, "con-name", HOTSPOT,
                            "autoconnect", "no", "ssid", HOTSPOT_SSID, "802-11-wireless.mode", "ap",
                            "802-11-wireless.band", "bg", "ipv4.method", "shared",
                            "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", self.password(),
                            "wifi-sec.proto", "rsn", "wifi-sec.pairwise", "ccmp", "wifi-sec.group", "ccmp",
                            "wifi-sec.pmf", "disable")
            if not ok:
                print("network: could not make the hotspot:", out, flush=True)
                self.offline_since = time.monotonic()   # try again after the wait
                return
        ok, out = nmcli("connection", "up", HOTSPOT, timeout=40)
        if ok:
            print("network: setup hotspot on", flush=True)
            self.hotspot_since = time.monotonic()
            with self.lock:
                self.mode, self.address = "hotspot", HOTSPOT_ADDRESS
        else:
            print("network: hotspot failed:", out, flush=True)
            self.offline_since = time.monotonic()

    def _hotspot_down(self):
        nmcli("connection", "down", HOTSPOT, timeout=20)

    def join(self, ssid, password):
        """Connects to ssid in the background; the outcome shows in status()."""
        if not self.enabled or self.joining:
            return False
        self.joining = True
        with self.lock:
            self.mode, self.ssid, self.error = "connecting", ssid, ""
        threading.Thread(target=self._join, args=(ssid, password), name="join", daemon=True).start()
        return True

    def _join(self, ssid, password):
        try:
            if self._hotspot_active():
                self._hotspot_down()
                time.sleep(3)
            nmcli("device", "wifi", "rescan", "ifname", self.wifi_device())
            time.sleep(5)
            cmd = ["--wait", "45", "device", "wifi", "connect", ssid]
            if password:
                cmd += ["password", password]
            ok, out = nmcli(*cmd, "ifname", self.wifi, timeout=60)
            if not ok and "no network with ssid" in out.lower():
                ok, out = nmcli(*cmd, "ifname", self.wifi, "hidden", "yes", timeout=60)
            if ok:
                print("network: joined", ssid, flush=True)
            else:
                print("network: could not join", ssid, out, flush=True)
                with self.lock:
                    self.error = f"{reason(out)}: {ssid}"
                # Back to the hotspot soon, so the phone can try again.
                self.offline_since = time.monotonic() - OFFLINE_WAIT + 10
                self.seen = time.monotonic()
        finally:
            self.joining = False
