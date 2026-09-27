import json
import tempfile
import unittest
from pathlib import Path

from pensieve_timeline.ops import _parser, run_ai, run_forensic


ROOT = Path(__file__).resolve().parents[1]


class VMProfileTests(unittest.TestCase):
    def test_ai_cli_enables_gliner_and_qwen_by_default(self):
        args = _parser().parse_args(["ai", "evidence.csv"])
        self.assertFalse(args.no_gliner)
        self.assertFalse(args.no_qwen)
        self.assertEqual(args.gliner_model, "urchade/gliner_multi-v2.1")
        self.assertEqual(args.qwen_model, "Qwen/Qwen3-0.6B")
        self.assertEqual(args.gliner_threshold, 0.45)

    def test_forensic_runner_has_no_ai_outputs(self):
        source = ROOT / "examples" / "first-investigation" / "dfir.csv"
        with tempfile.TemporaryDirectory() as folder:
            result = run_forensic(
                source,
                workspace_root=Path(folder),
                case_id="forensic-test",
            )

            self.assertEqual(result["profile"], "forensic")
            self.assertFalse(result["ai_enabled"])
            self.assertFalse(result["gliner_enabled"])
            self.assertFalse(result["qwen_enabled"])
            self.assertEqual(result["event_count"], 6)

            case = Path(folder) / "forensic-test"
            self.assertTrue((case / "timeline.jsonl").exists())
            self.assertTrue((case / "timeline.csv").exists())
            self.assertTrue((case / "timesketch.jsonl").exists())
            self.assertTrue((case / "correlations.jsonl").exists())
            self.assertTrue((case / "case.db").exists())
            self.assertTrue((case / "report.html").exists())
            self.assertFalse((case / "entities.jsonl").exists())
            self.assertFalse((case / "intelligence.json").exists())

            manifest = json.loads(
                (case / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["profile"], "forensic")

    def test_ai_vm_can_consume_forensic_timeline_without_rescoring(self):
        source = ROOT / "examples" / "first-investigation" / "dfir.csv"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            forensic = run_forensic(
                source,
                workspace_root=root,
                case_id="forensic-source",
            )
            timeline = Path(forensic["outputs"]["timeline_jsonl"])
            before = [
                json.loads(line)["risk_score"]
                for line in timeline.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            ai = run_ai(
                timeline,
                workspace_root=root,
                case_id="ai-handoff",
                canonical_timeline=True,
                gliner_enabled=False,
                qwen_enabled=False,
            )
            after_timeline = Path(ai["outputs"]["timeline_jsonl"])
            after = [
                json.loads(line)["risk_score"]
                for line in after_timeline.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual(ai["input_mode"], "canonical_timeline")
            self.assertEqual(before, after)
            self.assertTrue(
                Path(ai["outputs"]["evidence_packet_json"]).exists()
            )
            self.assertIsNone(ai["outputs"]["intelligence_json"])

    def test_vm_bootstrap_profiles_are_explicit(self):
        forensic = (
            ROOT / "deploy" / "vm" / "forensic" / "bootstrap.sh"
        ).read_text(encoding="utf-8")
        ai = (
            ROOT / "deploy" / "vm" / "ai" / "bootstrap.sh"
        ).read_text(encoding="utf-8")

        self.assertIn('install_python_profile ""', forensic)
        self.assertNotIn("[osint,llm]", forensic)
        self.assertIn("PENSIEVE_GLINER_ENABLED=1", ai)
        self.assertIn("PENSIEVE_QWEN_ENABLED=1", ai)
        self.assertIn('install_python_profile "[osint,llm]"', ai)
        self.assertIn("snapshot_download", ai)

    def test_dashboard_is_loopback_only_by_default(self):
        common = (
            ROOT / "deploy" / "vm" / "common" / "bootstrap-lib.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("--bind 127.0.0.1 --port 8080", common)


if __name__ == "__main__":
    unittest.main()
