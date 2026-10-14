#!/usr/bin/env python3
"""Reject paid or destructive OCI Terraform plans. No network calls."""
import json
import sys
import ipaddress
from pathlib import Path

ALLOWED = {
    "oci_core_vcn": "oci_core_vcn.radar",
    "oci_core_internet_gateway": "oci_core_internet_gateway.radar",
    "oci_core_route_table": "oci_core_route_table.radar",
    "oci_core_security_list": "oci_core_security_list.radar",
    "oci_core_subnet": "oci_core_subnet.radar",
    "oci_core_instance": "oci_core_instance.radar",
}

def verify(plan):
    changes = [c for c in plan.get("resource_changes", []) if c.get("mode") == "managed"]
    names = set()
    for change in changes:
        kind = change.get("type", "")
        address = change.get("address", "")
        if ALLOWED.get(kind) != address:
            raise ValueError("Unapproved resource: " + address)
        if change["change"].get("actions") != ["create"]:
            raise ValueError("Only creation is allowed; no updates or deletion: " + address)
        names.add(address)
    if names != set(ALLOWED.values()) or len(changes) != 6:
        raise ValueError("Expected exactly six standalone Flight Radar resources.")

    instance = next(c["change"]["after"] for c in changes if c["type"] == "oci_core_instance")
    if instance.get("shape") != "VM.Standard.E2.1.Micro":
        raise ValueError("Only the Always Free AMD E2.1.Micro shape is permitted.")
    if instance.get("preserve_boot_volume") is not False:
        raise ValueError("Orphaned boot volume forbidden.")
    sources = instance.get("source_details") or []
    if len(sources) != 1 or sources[0].get("boot_volume_size_in_gbs") != 50:
        raise ValueError("Exactly one 50GB boot volume required.")
    if instance.get("display_name") != "flight-radar-standalone-free":
        raise ValueError("Unexpected instance name.")
    if instance.get("shape_config"):
        raise ValueError("Shape config not allowed on AMD Micro.")

    sec = next(c["change"]["after"] for c in changes if c["type"] == "oci_core_security_list")
    rules = sec.get("ingress_security_rules") or []
    if len(rules) != 1 or rules[0].get("protocol") != "6":
        raise ValueError("Only one SSH TCP ingress rule permitted.")
    tcp = (rules[0].get("tcp_options") or [None])[0] or {}
    if tcp.get("min") != 22 or tcp.get("max") != 22:
        raise ValueError("Only SSH port 22 may be exposed.")
    net = ipaddress.ip_network(rules[0].get("source", ""), strict=False)
    if net.version != 4 or net.prefixlen != 32:
        raise ValueError("SSH must be restricted to one IPv4 /32.")

    for change in changes:
        tags = change["change"]["after"].get("freeform_tags") or {}
        if tags.get("project") != "flight-radar" or tags.get("workload") != "standalone":
            raise ValueError("Missing independent project tags on " + change["address"])
    return "PASS: six standalone OCI resources; E2 Micro; 50GB; SSH /32; no destructive actions."

if __name__ == "__main__":
    try:
        plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        print(verify(plan))
    except (IndexError, OSError, ValueError, KeyError, TypeError) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        sys.exit(1)
