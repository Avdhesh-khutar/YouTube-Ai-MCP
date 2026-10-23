import importlib.util
import io
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "check_free_video_space", "scripts/check_free_video_space.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CheckFreeVideoSpaceTests(unittest.TestCase):
    def test_rejects_malformed_space_id_without_network(self):
        with patch.object(module, "get_json") as get_json:
            self.assertEqual(module.inspect_space("not-a-space-id"), 2)
            get_json.assert_not_called()

    def test_prints_runtime_and_api_paths_without_generation(self):
        metadata = {
            "sdk": "gradio",
            "runtime": {"stage": "RUNNING", "hardware": "zero-gpu"},
            "private": False,
            "subdomain": "demo-owner-video",
        }
        schema = {
            "openapi": "3.0.0",
            "paths": {
                "/gradio_api/call/generate": {"post": {}},
                "/gradio_api/queue/status": {"get": {}},
            },
        }
        with patch.object(module, "get_json", side_effect=[
            (200, metadata), (200, schema)
        ]) as get_json:
            output = io.StringIO()
            with redirect_stdout(output):
                result = module.inspect_space("demo-owner/video")
        self.assertEqual(result, 0)
        rendered = output.getvalue()
        self.assertIn("Runtime stage: RUNNING", rendered)
        self.assertIn("Hardware: zero-gpu", rendered)
        self.assertIn("/gradio_api/call/generate", rendered)
        self.assertIn("No generation request was submitted", rendered)
        self.assertIn("does not prove image-to-video capability", rendered)
        self.assertEqual(get_json.call_count, 2)

    def test_reports_missing_public_api_without_running_generation(self):
        metadata = {
            "sdk": "gradio",
            "runtime": {"stage": "SLEEPING", "hardware": "cpu-basic"},
            "private": False,
            "subdomain": "demo-owner-video",
        }
        with patch.object(module, "get_json", side_effect=[
            (200, metadata),
            urllib.error.URLError("not reachable"),
            urllib.error.URLError("not reachable"),
        ]):
            output = io.StringIO()
            with redirect_stdout(output):
                result = module.inspect_space("demo-owner/video")
        self.assertEqual(result, 0)
        self.assertIn("API schema: not reachable", output.getvalue())
        self.assertIn("No generation request was submitted", output.getvalue())


if __name__ == "__main__":
    unittest.main()
