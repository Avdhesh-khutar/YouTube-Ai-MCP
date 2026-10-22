import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_cinematic_video as renderer


class CinematicRendererGuardTests(unittest.TestCase):
    def test_rejects_seconds_per_scene_outside_supported_range(self):
        with patch("sys.argv", ["generate_cinematic_video.py", "--seconds-per-scene", "13"]):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = renderer.main()
        self.assertEqual(result, 1)
        self.assertIn("between 2 and 12", stderr.getvalue())

    def test_missing_scene_images_fails_before_ffmpeg_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(renderer, "ffmpeg_available", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "No scene images found"):
                    renderer.render(Path(tmp), Path(tmp) / "out", 5)

    def test_renderer_report_policy_is_private_review_only(self):
        source = Path(renderer.__file__).read_text(encoding="utf-8")
        self.assertIn('"upload_enabled": False', source)
        self.assertIn("No upload or publishing was performed.", source)


if __name__ == "__main__":
    unittest.main()
