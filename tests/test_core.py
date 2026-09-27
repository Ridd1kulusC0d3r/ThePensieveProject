import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pensieve_timeline import __version__
from pensieve_timeline.correlation import correlate
from pensieve_timeline.integrity import fingerprint
from pensieve_timeline.io import read_jsonl, write_jsonl
from pensieve_timeline.pipeline import ingest
from pensieve_timeline.report import build_html
from pensieve_timeline.storage import save_case

class CoreTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,"-m","pensieve_timeline",*args],capture_output=True,text=True,check=False)

    def fixture(self,folder):
        path=Path(folder)/"events.csv"
        path.write_text(
            "Timestamp,Computer,Channel,EventID,User,ProcessId,Details\n"
            "2026-01-01T10:00:00Z,PC1,Security,4688,alice,42,Process created\n"
            "2026-01-01T10:00:05Z,PC1,Sysmon,1,alice,42,Process observed\n"
            "2026-01-01T10:01:00Z,PC1,System,7045,SYSTEM,99,Service installed\n",
            encoding="utf-8",
        )
        return path

    def test_version_and_doctor(self):
        self.assertEqual(self.run_cli("--version").stdout.strip(),__version__)
        result=self.run_cli("doctor")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_hash_preserves_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"evidência.bin"
            path.write_bytes(b"abc")
            self.assertEqual(fingerprint(path)["digest"],hashlib.sha256(b"abc").hexdigest())
            self.assertEqual(path.read_bytes(),b"abc")

    def test_ingest_roundtrip_correlation(self):
        with tempfile.TemporaryDirectory() as folder:
            events=ingest([self.fixture(folder)])
            self.assertEqual(len(events),3)
            self.assertEqual(events[-1].risk_score,35)
            output=Path(folder)/"timeline.jsonl"
            write_jsonl(events,output)
            self.assertEqual([e.event_id for e in read_jsonl(output)],[e.event_id for e in events])
            self.assertTrue(any("same_pid" in link.reasons for link in correlate(events,60)))

    def test_case_db_and_report(self):
        with tempfile.TemporaryDirectory() as folder:
            events=ingest([self.fixture(folder)])
            db=Path(folder)/"case.db"
            save_case(db,events,correlate(events))
            connection=sqlite3.connect(db)
            try:
                self.assertEqual(connection.execute("select count(*) from events").fetchone()[0],3)
            finally:
                connection.close()
            report=Path(folder)/"report.html"
            build_html(events,report)
            text=report.read_text(encoding="utf-8")
            self.assertIn("The Pensieve Project",text)
            self.assertIn("Process created",text)

    def test_optional_parser_gate(self):
        from pensieve_timeline.parsers import default_registry, extended_registry

        fake = Path("sample.evtx")
        with self.assertRaises(ValueError):
            default_registry().resolve(fake)
        self.assertEqual(extended_registry().resolve(fake).name, "python-evtx")

    def test_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.run_cli("hash",str(Path(folder)/"missing")).returncode,2)
            with self.assertRaises(ValueError):
                fingerprint(Path(folder))

if __name__=="__main__":
    unittest.main()
