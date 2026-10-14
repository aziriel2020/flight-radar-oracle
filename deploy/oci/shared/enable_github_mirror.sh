#!/usr/bin/env bash
# Safe update: only Flight Radar code/units. No edits to Nuvio/Caddy.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || exit 1
[[ -f flight_radar/oracle_sync.py && -f deploy/oci/shared/flight-radar-sync.service ]] || exit 1
systemctl is-active --quiet nuvio.service
systemctl is-active --quiet caddy.service
systemctl is-active --quiet flight-radar-gateway.service
test "$(curl -fsS -m 7 -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/_oracle/health)" = 200
install -m 644 flight_radar/oracle_sync.py /opt/flight-radar/flight_radar/oracle_sync.py
install -m 644 deploy/oci/shared/flight-radar-sync.service /etc/systemd/system/flight-radar-sync.service
install -m 644 deploy/oci/shared/flight-radar-sync.timer /etc/systemd/system/flight-radar-sync.timer
systemctl daemon-reload
# Do not hammer Google Flights from an IP returning blocked/unparsable responses.
systemctl disable --now flight-radar-collector.timer
systemctl enable --now flight-radar-sync.timer
systemctl start flight-radar-sync.service
curl -fsS -m 7 http://127.0.0.1:18080/health
echo
test "$(curl -fsS -m 7 -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/_oracle/health)" = 200
echo 'Oracle safe mirror enabled, provider-blocked scans disabled, Nuvio healthy.'
