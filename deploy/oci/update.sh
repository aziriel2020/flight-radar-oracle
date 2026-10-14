#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo "Run with sudo" >&2; exit 1; }
[[ -f flight_radar/__main__.py ]] || { echo "Run from project root" >&2; exit 1; }
[[ -f /etc/systemd/system/flight-radar.service ]] || { echo "Flight Radar not installed" >&2; exit 1; }
# This procedure touches ONLY the Flight Radar service and its own directories.
systemctl start flight-radar-backup.service
systemctl stop flight-radar.service
rsync -ar --delete --exclude=.git/ --exclude=.venv/ --exclude=config.json --exclude='*.sqlite*' --exclude='secrets.env' ./ /opt/flight-radar/
chown -R root:root /opt/flight-radar
systemctl start flight-radar.service
curl --fail --silent --show-error http://127.0.0.1:18080/health
printf '\nFlight Radar updated; other services untouched.\n'
