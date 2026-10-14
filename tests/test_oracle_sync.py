import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from flight_radar import oracle_sync


class OracleMirrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    @staticmethod
    def example_history():
        return {"schema_version": 1, "observations": [{
            "origin": "CDG", "destination": "FCO", "price_eur": 233.0,
            "source": "fast-flights-unofficial",
            "checked_at": "2026-10-14T21:30:27+00:00",
        }]}

    @staticmethod
    def example_market():
        return {"schema_version": 1, "status": "partial", "offers": [{
            "origin": "CDG", "destination": "FCO", "price_eur": 233.0,
            "source": "fast-flights-unofficial", "state": "observed",
            "checked_at": "2026-10-14T21:30:27+00:00",
        }]}

    def test_atomic_mirror_of_public_observations(self):
        docs = {"history": self.example_history(), "market": self.example_market()}
        with patch.object(oracle_sync, "fetch_json", side_effect=lambda name: docs[name]):
            oracle_sync.sync(self.root)
        self.assertEqual(json.loads((self.root / "history.json").read_text())["observations"][0]["price_eur"], 233.0)
        self.assertEqual(json.loads((self.root / "market.json").read_text())["status"], "partial")

    def test_upstream_outage_preserves_existing_local_data(self):
        old = {"schema_version": 1, "status": "ok", "offers": [{"id": 1}]}
        oracle_sync.atomic_write(self.root / "market.json", old)
        with patch.object(oracle_sync, "fetch_json", side_effect=URLError("offline")):
            with self.assertRaises(URLError):
                oracle_sync.sync(self.root)
        self.assertEqual(json.loads((self.root / "market.json").read_text()), old)

    def test_rejects_synthetic_fares_without_touching_local_history(self):
        oracle_sync.atomic_write(self.root / "history.json", {"previous": True})
        docs = {"history": self.example_history(), "market": self.example_market()}
        docs["market"]["offers"][0]["source"] = "DEMO_NON_REEL"
        with patch.object(oracle_sync, "fetch_json", side_effect=lambda name: docs[name]):
            with self.assertRaises(ValueError):
                oracle_sync.sync(self.root)
        self.assertEqual(json.loads((self.root / "history.json").read_text()), {"previous": True})
        self.assertFalse((self.root / "market.json").exists())

    def test_rejects_too_many_rows(self):
        docs = {"history": self.example_history(), "market": self.example_market()}
        docs["market"]["offers"] = [docs["market"]["offers"][0]] * 73
        with patch.object(oracle_sync, "fetch_json", side_effect=lambda name: docs[name]):
            with self.assertRaises(ValueError):
                oracle_sync.sync(self.root)

    def test_strict_file_permissions(self):
        oracle_sync.atomic_write(self.root / "history.json", self.example_history())
        import stat
        mode = stat.S_IMODE((self.root / "history.json").stat().st_mode)
        self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
