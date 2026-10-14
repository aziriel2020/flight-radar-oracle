import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flight_radar.engine import Offer, now
from flight_radar.market import compile_feed, normalize, run
from flight_radar.sources import make_plan


class MarketTests(unittest.TestCase):
    def sample(self, amount, when=None):
        when = when or now()
        departure = (now()+dt.timedelta(days=52)).date().isoformat()
        returning = (now()+dt.timedelta(days=58)).date().isoformat()
        obj = Offer("BRU", "LIS", departure, returning, amount, "TEST", "test-permitted", link="https://google.com/travel/flights", collected_at=when.isoformat())
        return normalize(obj, now())

    def test_price_is_observed_not_verified(self):
        _, offers = compile_feed([], [self.sample(125)])
        self.assertEqual(len(offers), 1)
        self.assertFalse(offers[0]["verified"])
        self.assertEqual(offers[0]["state"], "observed")
        self.assertIsNone(offers[0]["saving_pct"])

    def test_simulated_evidence_not_declared_bookable(self):
        reference=now()
        old = [self.sample(300, reference - dt.timedelta(days=i)) for i in range(1, 9)]
        row=self.sample(110, reference)
        _, offers=compile_feed(old,[row],reference)
        self.assertEqual(len(offers),1)
        self.assertTrue(offers[0]["potential_deal"])
        self.assertFalse(offers[0]["verified"])
        self.assertGreaterEqual(offers[0]["evidence_days"],8)

    def test_duplicate_same_day_does_not_fake_eight_days(self):
        reference=now()
        samples=[self.sample(300-i, reference-dt.timedelta(minutes=i)) for i in range(11)]
        _, offers=compile_feed(samples,[],reference)
        self.assertEqual(offers[0]["evidence_days"],1)
        self.assertIsNone(offers[0]["baseline_eur"])

    def test_old_quotes_not_public(self):
        old=self.sample(150,now()-dt.timedelta(days=2))
        _, offers=compile_feed([old],[])
        self.assertFalse(offers)

    def test_invalid_departure_rejected(self):
        o=Offer("BRU","LIS",(now()-dt.timedelta(days=1)).date().isoformat(),
                (now()+dt.timedelta(days=8)).date().isoformat(),120,"T","legal")
        with self.assertRaises(ValueError):
            normalize(o,now())

    def test_demo_data_rejected(self):
        fake=self.sample(100)
        fake["source"]="DEMO_NON_REEL"
        _, offers=compile_feed([],[fake])
        self.assertFalse(offers)

    def test_json_import_persists_history(self):
        now_=now()
        x=self.sample(170,now_)
        x.pop("checked_at")
        x.pop("state")
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            data=base/"test.json"
            data.write_text(json.dumps([x]),encoding="utf-8")
            history=base/"history.json"
            feed=base/"feed.json"
            config={"origins":["BRU"],"destinations":["LIS"],"days_ahead":[28],"stays":[7]}
            code=run(config,"json",input_file=str(data),history_path=str(history),feed_path=str(feed))
            self.assertEqual(code,0)
            saved=json.loads(feed.read_text())
            self.assertEqual(saved["status"],"ok")
            self.assertEqual(len(saved["offers"]),1)


if __name__=="__main__":
    unittest.main()
