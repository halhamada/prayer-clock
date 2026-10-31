# Copies the project to the Pi and installs it. Run from the project folder:
#   .\deploy\install-from-windows.ps1 -Address prayerclock.local -User pi
param(
    [string]$Address = "prayerclock.local",
    [string]$User = "pi"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$archive = Join-Path $env:TEMP "prayer-clock.tar.gz"

tar --exclude=__pycache__ -czf $archive -C $root app assets audio deploy
if ($LASTEXITCODE -ne 0) { throw "tar failed" }

$target = "$User@$Address"
Write-Host "Copying to $target (about 70 MB)..."
scp $archive "${target}:/tmp/prayer-clock.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

$remote = "set -e; rm -rf /tmp/prayer-clock; mkdir /tmp/prayer-clock; tar -xzf /tmp/prayer-clock.tar.gz -C /tmp/prayer-clock; " +
          "sudo bash /tmp/prayer-clock/deploy/setup.sh; rm -rf /tmp/prayer-clock /tmp/prayer-clock.tar.gz; sudo reboot"
ssh -t $target $remote
Remove-Item $archive
Write-Host "Installed. The Pi is rebooting; the clock appears when it comes back, then open http://${Address}:8080"
