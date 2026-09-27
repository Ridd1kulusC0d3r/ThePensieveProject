from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import unittest

from pensieve_timeline.model import ForensicEvent
from pensieve_timeline.osint.extract import extract_entities
from pensieve_timeline.osint.llm import parse_model_json
from pensieve_timeline.reasoning import (
    build_evidence_packet_v2,
    report_to_findings,
    snapshot_packet,
    validate_reasoning_payload,
    verify_evidence_packet_v2,
)


class AIReasoningTests(unittest.TestCase):
    def events(self):
        base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        first = ForensicEvent(
            base,
            "chat",
            "chat_export",
            "ops@example.org mentioned 10.10.10.5",
            host="LAB-01",
            user="alice",
            parser="test",
            record_locator="line:1",
            source_path="/private/case/source-one.txt",
            raw={"secret": "must-not-leak"},
        )
        second = ForensicEvent(
            base + timedelta(minutes=1),
            "dns",
            "dns",
            "query example.org",
            host="LAB-01",
            user="alice",
            parser="test",
            record_locator="line:2",
            raw={"another_secret": "also-private"},
        )
        return [first, second]

    def packet(self):
        events = self.events()
        return build_evidence_packet_v2(
            events,
            extract_entities(events),
            max_events=20,
        )

    def valid_payload(self):
        packet = self.packet()
        first, second = [row["event_id"] for row in packet["events"]]
        return {
            "summary": "The supplied events share investigative context.",
            "claims": [
                {
                    "level": "observation",
                    "statement": "The first event contains an email and IPv4 address.",
                    "evidence_event_ids": [first],
                    "rationale": "Both strings occur in the cited event snapshot.",
                    "alternatives": [],
                    "reported_confidence": 0.99,
                },
                {
                    "level": "hypothesis",
                    "statement": "The two events may belong to one activity sequence.",
                    "evidence_event_ids": [first, second],
                    "rationale": "They are close in time and share host/user context.",
                    "alternatives": [
                        "The events may be unrelated routine activity."
                    ],
                    "reported_confidence": 0.95,
                },
            ],
            "uncertainties": [
                "Temporal proximity alone does not establish causality."
            ],
            "next_questions": [
                "What additional artifacts cover the same time window?"
            ],
        }

    def test_packet_is_deterministic_and_excludes_raw(self):
        packet_one = self.packet()
        packet_two = self.packet()

        self.assertEqual(
            packet_one["packet_sha256"],
            packet_two["packet_sha256"],
        )
        self.assertEqual(snapshot_packet(packet_one), snapshot_packet(packet_two))
        self.assertEqual(
            verify_evidence_packet_v2(packet_one),
            packet_one["packet_sha256"],
        )

        serialized = json.dumps(packet_one)
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn("also-private", serialized)
        self.assertNotIn("/private/case/source-one.txt", serialized)
        self.assertNotIn('"raw"', serialized)
        self.assertNotIn('"source_path"', serialized)

    def test_packet_tampering_is_detected(self):
        packet = self.packet()
        tampered = deepcopy(packet)
        tampered["events"][0]["message"] = "changed"

        with self.assertRaises(ValueError):
            verify_evidence_packet_v2(tampered)

    def test_valid_report_has_citations_and_calibrated_support(self):
        packet = self.packet()
        report = validate_reasoning_payload(
            self.valid_payload(),
            packet,
            model_name="fake-model",
        )

        self.assertTrue(report["validation"]["valid"])
        self.assertEqual(report["packet_id"], packet["packet_id"])
        self.assertEqual(len(report["report_sha256"]), 64)
        self.assertEqual(len(report["claims"]), 2)

        for claim in report["claims"]:
            support = claim["calibrated_support"]
            self.assertTrue(support["not_probability"])
            self.assertFalse(
                support["basis"]["model_self_confidence_used"]
            )
            self.assertIn(
                support["label"],
                {"low", "moderate", "high"},
            )

        findings = report_to_findings(report, self.events())
        self.assertEqual(len(findings), 2)
        self.assertTrue(
            all(finding.status == "ai_proposed" for finding in findings)
        )

    def test_unknown_event_id_is_rejected(self):
        packet = self.packet()
        payload = self.valid_payload()
        payload["claims"][0]["evidence_event_ids"] = ["invented-event"]

        with self.assertRaises(ValueError):
            validate_reasoning_payload(payload, packet)

    def test_evidence_rewrite_fields_are_rejected(self):
        packet = self.packet()
        payload = self.valid_payload()
        payload["events"] = [{"event_id": "replacement"}]

        with self.assertRaises(ValueError):
            validate_reasoning_payload(payload, packet)

    def test_hypothesis_requires_alternative(self):
        packet = self.packet()
        payload = self.valid_payload()
        payload["claims"][1]["alternatives"] = []

        with self.assertRaises(ValueError):
            validate_reasoning_payload(payload, packet)

    def test_strict_json_parser_discards_thinking_and_rejects_trailing_text(self):
        parsed = parse_model_json(
            '<think>private reasoning</think>{"summary":"ok","claims":[],"uncertainties":[],"next_questions":[]}'
        )
        self.assertEqual(parsed["summary"], "ok")
        self.assertNotIn("private reasoning", json.dumps(parsed))

        with self.assertRaises(ValueError):
            parse_model_json(
                '{"summary":"ok","claims":[],"uncertainties":[],"next_questions":[]} trailing'
            )


if __name__ == "__main__":
    unittest.main()
