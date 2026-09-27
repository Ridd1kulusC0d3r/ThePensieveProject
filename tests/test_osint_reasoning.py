from datetime import datetime, timezone
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pensieve_timeline.analytics import rarity_analysis
from pensieve_timeline.case_engine import InvestigativeFinding
from pensieve_timeline.model import ForensicEvent
from pensieve_timeline.osint.extract import deduplicate_mentions, extract_entities
from pensieve_timeline.osint.graph import build_entity_graph, build_evidence_graph
from pensieve_timeline.osint.model import EntityMention
from pensieve_timeline.osint.llm import build_evidence_packet
from pensieve_timeline.storage import save_case

class OsintReasoningTests(unittest.TestCase):
    def events(self):
        base=datetime(2026,1,1,10,0,tzinfo=timezone.utc)
        return [
            ForensicEvent(base,"synthetic","chat_export","Contato ops@example.org de 10.10.10.5 falou com @analyst_br sobre https://example.org/a",host="LAB-01",user="alice",parser="test",record_locator="line:1"),
            ForensicEvent(base.replace(minute=1),"synthetic","chat_export","@analyst_br voltou a mencionar example.org",host="LAB-01",user="alice",parser="test",record_locator="line:2"),
            ForensicEvent(base.replace(minute=2),"synthetic","dns","consulta para rare.example.net",host="LAB-01",user="bob",parser="test",record_locator="line:3"),
        ]

    def test_extract_is_grounded(self):
        events=self.events()
        mentions=extract_entities(events)
        values={(m.label,m.text) for m in mentions}
        self.assertIn(("email","ops@example.org"),values)
        self.assertIn(("ipv4","10.10.10.5"),values)
        self.assertIn(("social_handle","@analyst_br"),values)
        self.assertTrue(all(m.event_id in {e.event_id for e in events} for m in mentions))

    def test_normalization_and_multi_extractor_dedup(self):
        regex = EntityMention(
            "event-1",
            "Ops@Example.ORG",
            "email",
            4,
            19,
            1.0,
            "regex:email",
        )
        model = EntityMention(
            "event-1",
            "Ops@Example.ORG",
            "email address",
            4,
            19,
            0.91,
            "gliner:test-model",
        )
        self.assertEqual(regex.normalized_value, "ops@example.org")
        self.assertEqual(regex.mention_id, model.mention_id)

        merged = deduplicate_mentions([model, regex])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].extractor, "regex:email")
        self.assertEqual(
            merged[0].corroborated_by,
            ["gliner:test-model", "regex:email"],
        )
        self.assertEqual(merged[0].confidence_kind, "deterministic")
        self.assertEqual(len(merged[0].evidence_hash), 64)

    def test_graph_aggregates_canonical_values(self):
        left = EntityMention(
            "event-a",
            "Ops@Example.ORG",
            "email",
            0,
            15,
            1.0,
            "regex:email",
        )
        right = EntityMention(
            "event-b",
            "ops@example.org",
            "email",
            0,
            15,
            0.8,
            "gliner:test",
        )
        graph = build_entity_graph([left, right])
        self.assertEqual(len(graph["nodes"]), 1)
        self.assertEqual(
            graph["nodes"][0]["normalized"],
            "ops@example.org",
        )
        self.assertEqual(
            set(graph["nodes"][0]["event_ids"]),
            {"event-a", "event-b"},
        )

    def test_graph_semantics(self):
        events=self.events()
        mentions=extract_entities(events)
        graph=build_entity_graph(mentions)
        self.assertIn("not proof of identity",graph["semantics"])
        self.assertGreater(len(graph["edges"]),0)
        evidence=build_evidence_graph(events,mentions)
        self.assertIn("identity_rule",evidence["semantics"])
        self.assertTrue(any(edge["type"]=="mentioned_in" for edge in evidence["edges"]))

    def test_llm_packet_excludes_raw(self):
        events=self.events()
        events[0].raw={"secret_internal_field":"do-not-export"}
        packet=build_evidence_packet(events,extract_entities(events))
        self.assertNotIn("secret_internal_field",json.dumps(packet))
        self.assertFalse(packet["policy"]["external_enrichment"])

    def test_findings_and_rarity(self):
        finding=InvestigativeFinding("hypothesis","Synthetic",["missing"],"exercise",["alternative"],.4)
        with self.assertRaises(ValueError):
            finding.validate(self.events())
        findings=rarity_analysis(self.events())
        self.assertEqual(len(findings),3)
        self.assertTrue(all(0<=f.score<=1 for f in findings))

    def test_case_db_keeps_entities_derived(self):
        events=self.events()
        mentions=extract_entities(events)
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/"case.db"
            save_case(db,events,entities=mentions)
            connection=sqlite3.connect(db)
            try:
                self.assertEqual(connection.execute("select count(*) from events").fetchone()[0],len(events))
                self.assertEqual(connection.execute("select count(*) from entity_mentions").fetchone()[0],len(mentions))
                columns={row[1] for row in connection.execute("pragma table_info(entity_mentions)")}
                self.assertIn("normalized_value",columns)
                self.assertIn("confidence_kind",columns)
                stored=connection.execute(
                    "select normalized_value, confidence_kind, evidence_hash from entity_mentions limit 1"
                ).fetchone()
                self.assertTrue(stored[0])
                self.assertIn(stored[1],{"deterministic","model","derived"})
                self.assertEqual(len(stored[2]),64)
            finally:
                connection.close()

if __name__=="__main__":
    unittest.main()
