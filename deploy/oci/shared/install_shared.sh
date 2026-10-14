#!/usr/bin/env bash
# Isolated one-time install of Flight Radar on the existing Nuvio OCI VM.
# Never touches /opt/nuvio, /etc/nuvio, Nuvio services or Caddy configuration.
set -Eeuo pipefail
umask 027
[[ $EUID -eq 0 ]] || { echo 'ERROR: run as root' >&2; exit 1; }
[[ -f flight_radar/oracle_gateway.py && -f flight_radar/market.py ]] || { echo 'ERROR: start in Flight Radar repo root' >&2; exit 1; }

# Hard preflight: preserve production health, headroom, and ownership of local port.
[[ "$(systemctl is-active nuvio)" == active && "$(systemctl is-active caddy)" == active ]] || { echo 'ERROR: Nuvio/Caddy not active; aborting' >&2; exit 1; }
[[ "$(curl -fsS -m 6 -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/_oracle/health)" == 200 ]] || { echo 'ERROR: Nuvio health is not 200; aborting' >&2; exit 1; }
[[ ! -e /etc/systemd/system/flight-radar-gateway.service ]] || { echo 'ERROR: Flight Radar already installed' >&2; exit 1; }
available_mem="$(free -m | awk '/^Mem:/ {print $7}')"
available_disk="$(df -Pm / | awk 'NR==2 {print $4}')"
[[ "${available_mem:-0}" -ge 1500 && "${available_disk:-0}" -ge 3000 ]] || { echo "ERROR: low spare resources: RAM $available_mem MB / disk $available_disk MB" >&2; exit 1; }
python3 - <<'PY'
import socket
with socket.socket() as s:
    s.bind(('127.0.0.1', 18080))
PY

# Only Flight Radar files and Linux user are created. No network firewall changes.
if ! python3 -c 'import venv' >/dev/null 2>&1; then
  echo 'ERROR: python3-venv unavailable. Install it separately after assessing the server.' >&2
  exit 1
fi
command -v git >/dev/null || { echo 'ERROR: git unavailable' >&2; exit 1; }
# Minimal Python bootstrap only if the image lacks pip-enabled virtual environments.
probe="$(mktemp -d /tmp/flight-radar-venv.XXXXXX)"
if ! python3 -m venv "$probe/venv" >/dev/null 2>&1; then
  pyver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  rm -rf "$probe"
  echo "Installing missing python${pyver}-venv (no Nuvio service restart)."
  export DEBIAN_FRONTEND=noninteractive
  sudo -n apt-get update -qq
  sudo -n apt-get install -y --no-install-recommends "python${pyver}-venv"
  probe="$(mktemp -d /tmp/flight-radar-venv.XXXXXX)"
  python3 -m venv "$probe/venv"
fi
rm -rf "$probe"
id flightradar >/dev/null 2>&1 || useradd --system --home-dir /var/lib/flight-radar --shell /usr/sbin/nologin flightradar
install -d -o root -g root -m 755 /opt/flight-radar /etc/flight-radar
install -d -o flightradar -g flightradar -m 700 /var/lib/flight-radar /var/lib/flight-radar/data /var/lib/flight-radar/backups
install -d -o flightradar -g flightradar -m 750 /var/lib/flight-radar/images /var/lib/flight-radar/images/destinations
cp -a flight_radar requirements-optional.txt /opt/flight-radar/
python3 -m venv /opt/flight-radar/.venv
/opt/flight-radar/.venv/bin/python -m pip install --disable-pip-version-check -r /opt/flight-radar/requirements-optional.txt
chown -R root:root /opt/flight-radar
# The isolated unprivileged account must traverse the venv; no write access granted.
chmod -R a+rX /opt/flight-radar/.venv
if [[ ! -f /etc/flight-radar/config.json ]]; then
  install -o root -g flightradar -m 640 config.json /etc/flight-radar/config.json
fi
for name in history market; do
  if [[ ! -f "/var/lib/flight-radar/data/$name.json" ]]; then
    install -o flightradar -g flightradar -m 600 "data/$name.json" "/var/lib/flight-radar/data/$name.json"
  fi
done
runuser -u flightradar -- /opt/flight-radar/.venv/bin/python -m flight_radar.city_art --output /var/lib/flight-radar/images/destinations

for component in gateway collector backup; do
  install -m 644 "deploy/oci/shared/flight-radar-$component.service" "/etc/systemd/system/flight-radar-$component.service"
done
for timer in collector backup; do
  install -m 644 "deploy/oci/shared/flight-radar-$timer.timer" "/etc/systemd/system/flight-radar-$timer.timer"
done
install -d -m 755 /opt/flight-radar/deploy/oci/shared
install -m 755 deploy/oci/shared/backup.sh /opt/flight-radar/deploy/oci/shared/backup.sh
systemctl daemon-reload
systemctl enable --now flight-radar-gateway.service
systemctl enable --now flight-radar-collector.timer flight-radar-backup.timer
curl -fsS --max-time 7 http://127.0.0.1:18080/health
test "$(find /var/lib/flight-radar/images/destinations -maxdepth 1 -type f -name '*.svg' | wc -l)" -ge 10
[[ "$(curl -fsS -m 6 -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/_oracle/health)" == 200 ]]
echo 'Flight Radar isolated gateway and timers installed. Nuvio production remains healthy.'
echo 'No public ingress or Caddy routes were altered.'
