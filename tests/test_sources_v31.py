import sys
import types
import unittest
from unittest.mock import patch

from flight_radar.sources import fast_flights_search


class FakeQuery:
    def url(self):
        return "https://www.google.com/travel/flights/search?tfs=test"


class SourceV31Tests(unittest.TestCase):
    def _source(self, listings):
        fake = types.ModuleType("fast_flights")
        fake.FlightQuery = lambda **kwargs: types.SimpleNamespace(**kwargs)
        fake.Passengers = lambda **kwargs: kwargs
        fake.create_query = lambda **kwargs: FakeQuery()
        fake.get_flights = lambda q: listings
        return fake

    def test_result_list_v31(self):
        flights=[
            types.SimpleNamespace(price=129,airlines=["LH"],flights=[object()]),
            types.SimpleNamespace(price=194,airlines=["KL"],flights=[object(),object()]),
        ]
        with patch.dict(sys.modules, {"fast_flights":self._source(flights)}):
            offers=fast_flights_search("BRU","LIS","2027-01-10","2027-01-17")
        self.assertEqual(len(offers),2)
        self.assertEqual([o.stops for o in offers],[0,1])
        self.assertEqual([o.carrier for o in offers],["LH","KL"])
        self.assertIn("tfs=test",offers[0].link)
        self.assertIn("may not include the return",offers[0].details)

    def test_missing_segments_not_published(self):
        listings=[types.SimpleNamespace(price=25,airlines=["LH"],flights=[])]
        with patch.dict(sys.modules, {"fast_flights":self._source(listings)}):
            offers=fast_flights_search("BRU","LIS","2027-01-10","2027-01-17")
        self.assertEqual(offers, [])

if __name__=="__main__":
    unittest.main()
