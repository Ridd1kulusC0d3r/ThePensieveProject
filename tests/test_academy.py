import json
import unittest
from pathlib import Path

from pensieve_timeline.pipeline import ingest


ROOT = Path(__file__).resolve().parents[1]


class AcademyTests(unittest.TestCase):
    def test_catalog_has_three_tracks_and_shared_core(self):
        catalog = json.loads((ROOT / "academy" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["format_version"], "2.0")
        self.assertEqual(set(catalog["tracks"]), {"DFIR", "OSINT", "HYBRID"})
        self.assertEqual([m["id"] for m in catalog["shared_core"]], ["C00", "C01", "C02"])
        for track in catalog["tracks"].values():
            self.assertTrue(track["dataset"])
            self.assertTrue(track["missions"])

    def test_first_investigation_datasets_ingest(self):
        expected = {
            "dfir.csv": 6,
            "osint.csv": 5,
            "hybrid.csv": 8,
        }
        base = ROOT / "examples" / "first-investigation"
        for name, count in expected.items():
            events = ingest([base / name])
            self.assertEqual(len(events), count, name)
            self.assertEqual(len({event.event_id for event in events}), count, name)
            self.assertTrue(all(event.record_locator for event in events), name)
            self.assertTrue(all(event.parser for event in events), name)

    def test_notebook_is_valid_and_models_are_opt_in(self):
        path = ROOT / "colab" / "first_investigation.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        self.assertGreaterEqual(len(notebook["cells"]), 20)

        source = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
        )
        self.assertIn("TRACK = 'HYBRID'", source)
        self.assertIn("USE_GLINER = False", source)
        self.assertIn("USE_QWEN = False", source)
        self.assertIn("academy-progress.json", source)
        self.assertIn("evidence-packet", source)
        self.assertIn("Capstone", source)

    def test_progress_schema_and_tutor_manifest_are_connected(self):
        schema = json.loads(
            (ROOT / "schemas" / "academy-progress.schema.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (ROOT / "academy" / "ai-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["track"]["enum"], ["DFIR", "OSINT", "HYBRID"])
        self.assertIn(
            "schemas/academy-progress.schema.json",
            manifest["machine_readable_assets"],
        )
        self.assertIn("Correlation does not prove causality.", manifest["epistemic_contract"])


if __name__ == "__main__":
    unittest.main()
