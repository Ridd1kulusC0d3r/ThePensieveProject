import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pensieve_timeline.api import _rows, _stats
from pensieve_timeline.model import ForensicEvent
from pensieve_timeline.storage import save_case


class ReadOnlyApiTests(unittest.TestCase):
    def make_case(self, folder):
        event = ForensicEvent(
            datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            "Security",
            "evtx",
            "Synthetic API contract event",
            host="LAB01",
            event_code="4688",
            source_path="fixture.evtx",
            record_locator="event_record_id:1",
            parser="test",
            parser_version="1",
            raw={"secret_for_test": "not returned by default"},
        )
        path = Path(folder) / "case.db"
        save_case(path, [event])
        return path, event

    def test_storage_queries_are_read_only_and_hide_raw_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            path, event = self.make_case(folder)
            rows = _rows(path, "events", filters={"event_id": event.event_id})
            self.assertEqual(rows[0]["event_id"], event.event_id)
            self.assertNotIn("raw_json", rows[0])
            self.assertEqual(_stats(path)["events"], 1)

    @unittest.skipUnless(importlib.util.find_spec("fastapi"), "FastAPI optional extra not installed")
    def test_fastapi_routes_are_created(self):
        from pensieve_timeline.api import create_app

        with tempfile.TemporaryDirectory() as folder:
            path, _ = self.make_case(folder)
            app = create_app(path)
            routes = {route.path for route in app.routes}
            self.assertTrue({"/health", "/stats", "/events", "/entities", "/correlations"} <= routes)


if __name__ == "__main__":
    unittest.main()
