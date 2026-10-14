import datetime as dt, tempfile, unittest
from pathlib import Path
from flight_radar.engine import Offer,connect,ingest,stamp,now,list_candidates
class EngineTest(unittest.TestCase):
 def test_discount(self):
  with tempfile.TemporaryDirectory() as tmp:
   with connect(str(Path(tmp)/"test.sqlite")) as c:
    out=str((now()+dt.timedelta(days=60)).date());ret=str((now()+dt.timedelta(days=65)).date())
    for i in range(9):
     o=Offer("BRU","LIS",out,ret,350+i,"Air Test","fixture",link="https://example.com",collected_at=stamp(now()-dt.timedelta(days=10-i)))
     self.assertIsNone(ingest(c,o)["candidate_id"])
    deal=ingest(c,Offer("BRU","LIS",out,ret,150,"Air Test","fixture",link="https://example.com"))
    self.assertIsNotNone(deal["candidate_id"])
    self.assertEqual(len(list_candidates(c)),1)
 def test_bad_iata(self):
  with self.assertRaises(ValueError):Offer("BRUSSELS","LIS","2027-01-01","","120","X","fixture").validated()
if __name__=="__main__":unittest.main()
