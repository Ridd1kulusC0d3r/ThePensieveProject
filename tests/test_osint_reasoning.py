from datetime import datetime,timezone
import json,sqlite3,tempfile,unittest
from pathlib import Path
from pensieve_timeline.analytics import rarity_analysis
from pensieve_timeline.case_engine import InvestigativeFinding
from pensieve_timeline.model import ForensicEvent
from pensieve_timeline.osint.extract import extract_entities
from pensieve_timeline.osint.graph import build_entity_graph
from pensieve_timeline.osint.llm import build_evidence_packet
from pensieve_timeline.storage import save_case

class OsintReasoningTests(unittest.TestCase):
    def events(self):
        base=datetime(2026,1,1,10,0,tzinfo=timezone.utc)
        return [
          ForensicEvent(base,"synthetic","chat_export","Contato ops@example.org de 10.10.10.5 falou com @analyst_br sobre https://example.org/a",host="LAB-01",user="alice",parser="test",record_locator="line:1"),
          ForensicEvent(base.replace(minute=1),"synthetic","chat_export","@analyst_br voltou a mencionar example.org",host="LAB-01",user="alice",parser="test",record_locator="line:2"),
          ForensicEvent(base.replace(minute=2),"synthetic","dns","consulta para rare.example.net",host="LAB-01",user="bob",parser="test",record_locator="line:3")]
    def test_extract_is_grounded(self):
        events=self.events();mentions=extract_entities(events);values={(m.label,m.text) for m in mentions}
        self.assertIn(("email","ops@example.org"),values);self.assertIn(("ipv4","10.10.10.5"),values);self.assertIn(("social_handle","@analyst_br"),values)
        self.assertTrue(all(m.event_id in {e.event_id for e in events} for m in mentions))
    def test_graph_semantics(self):
        graph=build_entity_graph(extract_entities(self.events()));self.assertIn("not proof of identity",graph["semantics"]);self.assertGreater(len(graph["edges"]),0)
    def test_llm_packet_excludes_raw(self):
        events=self.events();events[0].raw={"secret_internal_field":"do-not-export"};packet=build_evidence_packet(events,extract_entities(events))
        self.assertNotIn("secret_internal_field",json.dumps(packet));self.assertFalse(packet["policy"]["external_enrichment"])
    def test_findings_and_rarity(self):
        finding=InvestigativeFinding("hypothesis","Synthetic",["missing"],"exercise",["alternative"],.4)
        with self.assertRaises(ValueError):finding.validate(self.events())
        findings=rarity_analysis(self.events());self.assertEqual(len(findings),3);self.assertTrue(all(0<=f.score<=1 for f in findings))
    def test_case_db_keeps_entities_derived(self):
        events=self.events();mentions=extract_entities(events)
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"case.db";save_case(db,events,entities=mentions)
            with sqlite3.connect(db) as c:
                self.assertEqual(c.execute("select count(*) from events").fetchone()[0],len(events))
                self.assertEqual(c.execute("select count(*) from entity_mentions").fetchone()[0],len(mentions))

if __name__=="__main__":unittest.main()
