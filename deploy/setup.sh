#!/bin/bash
# Installs the prayer clock on Raspberry Pi OS Lite. Run from the unpacked project: sudo bash deploy/setup.sh
# Safe to run again for an update: it keeps the data dir's schedule, settings and uploaded audio.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/prayer-clock
DATA=/var/lib/prayer-clock
SERVICE_USER=prayerclock

echo "== packages"
apt-get update
apt-get install -y --no-install-recommends python3 python3-pygame mpg123 alsa-utils systemd-timesyncd

echo "== app"
id "$SERVICE_USER" >/dev/null 2>&1 || useradd --system --home-dir "$DATA" --shell /usr/sbin/nologin "$SERVICE_USER"
usermod -aG video,audio,render "$SERVICE_USER"
if [ "$SRC" != "$APP" ]; then
    mkdir -p "$APP"
    rm -rf "$APP/app" "$APP/assets"
    cp -r "$SRC/app" "$SRC/assets" "$APP/"
fi
mkdir -p "$DATA/audio"
cp -n "$SRC"/audio/* "$DATA/audio/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA"

echo "== clock"
timedatectl set-timezone Asia/Riyadh
timedatectl set-ntp true
# Setting the time from the dashboard, for when the device has no internet. Only date, and only -s.
SUDOERS=/etc/sudoers.d/prayer-clock
echo "$SERVICE_USER ALL=(root) NOPASSWD: /usr/bin/date -s @*" > "$SUDOERS.new"
chmod 440 "$SUDOERS.new"
visudo -cf "$SUDOERS.new"
mv "$SUDOERS.new" "$SUDOERS"

echo "== boot"
BOOT=/boot/firmware
[ -d "$BOOT" ] || BOOT=/boot
CMDLINE="$BOOT/cmdline.txt"
CONFIG="$BOOT/config.txt"
[ -f "$CMDLINE.before-prayer-clock" ] || cp "$CMDLINE" "$CMDLINE.before-prayer-clock"
[ -f "$CONFIG.before-prayer-clock" ] || cp "$CONFIG" "$CONFIG.before-prayer-clock"
# 720p keeps a full-screen redraw easy on a Zero; D keeps the output on while the TV is off at boot.
for arg in video=HDMI-A-1:1280x720@60D vt.global_cursor_default=0 consoleblank=0 logo.nologo quiet loglevel=1; do
    key="${arg%%=*}"
    if [ "$key" = video ]; then pattern="video=HDMI-A-1:[^ ]*"; else pattern="(^| )$key(=[^ ]*)?( |$)"; fi
    grep -Eq "$pattern" "$CMDLINE" || sed -i "1 s|\$| $arg|" "$CMDLINE"
done
grep -q '^dtoverlay=vc4-kms-v3d' "$CONFIG" || echo 'dtoverlay=vc4-kms-v3d' >> "$CONFIG"
grep -q '^dtparam=audio=on' "$CONFIG" || echo 'dtparam=audio=on' >> "$CONFIG"
grep -q '^disable_splash=1' "$CONFIG" || echo 'disable_splash=1' >> "$CONFIG"

echo "== service"
cp "$SRC/deploy/prayer-clock.service" /etc/systemd/system/
# The clock owns the screen; a login prompt on tty1 would flash through it.
systemctl disable --now getty@tty1.service || true
systemctl daemon-reload
systemctl enable prayer-clock.service

echo "== done. Reboot to start: sudo reboot"
