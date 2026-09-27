import hashlib,json,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from pensieve_timeline import __version__
from pensieve_timeline.correlation import correlate
from pensieve_timeline.integrity import fingerprint
from pensieve_timeline.io import read_jsonl,write_jsonl
from pensieve_timeline.pipeline import ingest
from pensieve_timeline.report import build_html
from pensieve_timeline.storage import save_case

class CoreTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,"-m","pensieve_timeline",*args],capture_output=True,text=True,check=False)
    def fixture(self,folder):
        p=Path(folder)/"events.csv"
        p.write_text("Timestamp,Computer,Channel,EventID,User,ProcessId,Details\n2026-01-01T10:00:00Z,PC1,Security,4688,alice,42,Process created\n2026-01-01T10:00:05Z,PC1,Sysmon,1,alice,42,Process observed\n2026-01-01T10:01:00Z,PC1,System,7045,SYSTEM,99,Service installed\n",encoding="utf-8")
        return p
    def test_version_and_doctor(self):
        self.assertEqual(self.run_cli("--version").stdout.strip(),__version__)
        r=self.run_cli("doctor"); self.assertEqual(r.returncode,0,r.stderr); self.assertTrue(json.loads(r.stdout)["ok"])
    def test_hash_preserves_input(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"evidência.bin";p.write_bytes(b"abc")
            self.assertEqual(fingerprint(p)["digest"],hashlib.sha256(b"abc").hexdigest());self.assertEqual(p.read_bytes(),b"abc")
    def test_ingest_roundtrip_correlation(self):
        with tempfile.TemporaryDirectory() as d:
            events=ingest([self.fixture(d)]);self.assertEqual(len(events),3);self.assertEqual(events[-1].risk_score,35)
            out=Path(d)/"timeline.jsonl";write_jsonl(events,out);self.assertEqual([e.event_id for e in read_jsonl(out)],[e.event_id for e in events])
            self.assertTrue(any("same_pid" in link.reasons for link in correlate(events,60)))
    def test_case_db_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            events=ingest([self.fixture(d)]);db=Path(d)/"case.db";save_case(db,events,correlate(events))
            with sqlite3.connect(db) as c:self.assertEqual(c.execute("select count(*) from events").fetchone()[0],3)
            report=Path(d)/"report.html";build_html(events,report);text=report.read_text();self.assertIn("The Pensieve Project",text);self.assertIn("Process created",text)
    def test_errors(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_cli("hash",str(Path(d)/"missing")).returncode,2)
            with self.assertRaises(ValueError):fingerprint(Path(d))

if __name__=="__main__":unittest.main()
