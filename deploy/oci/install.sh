#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo "Run with sudo" >&2; exit 1; }
[[ -f flight_radar/__main__.py && -f config.json ]] || { echo "Run from project root" >&2; exit 1; }
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv rsync
id flightradar >/dev/null 2>&1 || useradd --system --home /var/lib/flight-radar --shell /usr/sbin/nologin flightradar
install -d -o root -g root -m 755 /opt/flight-radar /etc/flight-radar
install -d -o flightradar -g flightradar -m 700 /var/lib/flight-radar
rsync -ar --delete --exclude=.git/ --exclude=.venv/ --exclude=config.json --exclude='*.sqlite*' ./ /opt/flight-radar/
chown -R root:root /opt/flight-radar
python3 -m venv /opt/flight-radar/.venv
if [[ ! -f /etc/flight-radar/config.json ]];then install -o root -g flightradar -m 640 config.json /etc/flight-radar/config.json;fi
(cd /opt/flight-radar && runuser -u flightradar -- /opt/flight-radar/.venv/bin/python -m flight_radar --db /var/lib/flight-radar/flight_radar.sqlite --config /etc/flight-radar/config.json init)
install -m 644 deploy/oci/flight-radar.service /etc/systemd/system/flight-radar.service
systemctl daemon-reload
systemctl enable --now flight-radar.service
systemctl --no-pager status flight-radar.service | head -20 || true
echo "Installed. Dashboard binds only to localhost:8080 (SSH tunnel required)."
