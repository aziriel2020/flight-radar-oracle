#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
source_dir=/var/lib/flight-radar/data
dest_dir=/var/lib/flight-radar/backups
mkdir -p "$dest_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
tar -C "$source_dir" -czf "$dest_dir/flight-radar-$timestamp.tgz.writing" history.json market.json
mv "$dest_dir/flight-radar-$timestamp.tgz.writing" "$dest_dir/flight-radar-$timestamp.tgz"
find "$dest_dir" -name 'flight-radar-*.tgz' -type f -mtime +14 -delete
