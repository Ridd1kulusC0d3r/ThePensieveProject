import json
import unittest
from pathlib import Path

from pensieve_timeline.webapp import _parser, _safe_filename, _safe_name, _ui_html


ROOT = Path(__file__).resolve().parents[1]


class WebAppContractTests(unittest.TestCase):
    def test_safe_names_drop_path_traversal(self):
        self.assertEqual(_safe_name("../../CASE 001"), "..-..-CASE-001")
        self.assertEqual(_safe_filename("../../evidence.csv"), "evidence.csv")
        self.assertNotIn("/", _safe_filename("../../evidence.csv"))

    def test_web_cli_defaults_to_colab_port(self):
        args = _parser().parse_args([])
        self.assertEqual(args.port, 3000)
        self.assertEqual(args.host, "127.0.0.1")

    def test_frontend_defaults_to_ai_with_gliner_and_qwen_checked(self):
        html = _ui_html()
        self.assertIn('option value="ai" selected', html)
        self.assertIn('id="gliner" type="checkbox" checked', html)
        self.assertIn('id="qwen" type="checkbox" checked', html)
        self.assertIn("Forensic Core · sem IA", html)
        self.assertIn("AI Analyst · GLiNER + Qwen", html)
        self.assertIn("Evidence Packet v2", html)

    def test_colab_launcher_installs_ui_and_ai_extras(self):
        notebook = json.loads(
            (ROOT / "colab" / "pensieve_frontend.ipynb").read_text(
                encoding="utf-8"
            )
        )
        source = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
        )
        self.assertIn("[ui,osint,llm]", source)
        self.assertIn("'--port','3000'", source)
        self.assertIn("serve_kernel_port_as_window(3000)", source)
        self.assertIn("urchade/gliner_multi-v2.1", source)
        self.assertIn("Qwen/Qwen3-0.6B", source)


if __name__ == "__main__":
    unittest.main()
