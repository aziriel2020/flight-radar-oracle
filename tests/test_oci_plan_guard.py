"""Regression tests for isolated OCI Terraform plan guard."""
import copy
import importlib.util
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().parents[1] / "infra" / "oci-micro" / "guard_plan.py"
SPEC = importlib.util.spec_from_file_location("oci_plan_guard", GUARD_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

def valid_plan():
    shared = {"freeform_tags": {"project": "flight-radar", "workload": "standalone"}}
    names = [
        "oci_core_vcn", "oci_core_internet_gateway", "oci_core_route_table",
        "oci_core_security_list", "oci_core_subnet", "oci_core_instance",
    ]
    items = []
    for kind in names:
        after = copy.deepcopy(shared)
        if kind == "oci_core_security_list":
            after["ingress_security_rules"] = [{
                "protocol": "6", "source": "203.0.113.42/32",
                "tcp_options": [{"min": 22, "max": 22}]
            }]
        if kind == "oci_core_instance":
            after.update({
                "shape": "VM.Standard.E2.1.Micro",
                "preserve_boot_volume": False,
                "display_name": "flight-radar-standalone-free",
                "source_details": [{"boot_volume_size_in_gbs": 50}],
            })
        items.append({
            "mode": "managed", "type": kind, "address": kind + ".radar",
            "change": {"actions": ["create"], "after": after}
        })
    return {"resource_changes": items}

class TestOraclePlanGuard(unittest.TestCase):
    def test_valid_free_plan(self):
        self.assertIn("PASS", MODULE.verify(valid_plan()))

    def test_reject_paid_compute(self):
        plan = valid_plan()
        plan["resource_changes"][-1]["change"]["after"]["shape"] = "VM.Standard.A1.Flex"
        with self.assertRaises(ValueError):
            MODULE.verify(plan)

    def test_reject_terraform_deletion(self):
        plan = valid_plan()
        plan["resource_changes"][0]["change"]["actions"] = ["delete", "create"]
        with self.assertRaises(ValueError):
            MODULE.verify(plan)

    def test_reject_public_ssh(self):
        plan = valid_plan()
        plan["resource_changes"][3]["change"]["after"]["ingress_security_rules"][0]["source"] = "0.0.0.0/0"
        with self.assertRaises(ValueError):
            MODULE.verify(plan)

    def test_reject_foreign_resource(self):
        plan = valid_plan()
        plan["resource_changes"][0]["address"] = "oci_core_vcn.nuvio"
        with self.assertRaises(ValueError):
            MODULE.verify(plan)

    def test_reject_large_boot_volume(self):
        plan = valid_plan()
        plan["resource_changes"][-1]["change"]["after"]["source_details"][0]["boot_volume_size_in_gbs"] = 120
        with self.assertRaises(ValueError):
            MODULE.verify(plan)

if __name__ == "__main__":
    unittest.main()
