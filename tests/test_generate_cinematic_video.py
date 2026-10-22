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

    def test_scene_plan_controls_render_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            scenes.mkdir()
            for number in range(1, 5):
                (scenes / f"scene-{number:02d}.png").write_bytes(b"image placeholder")
            plan = {
                "scenes": [
                    {
                        "scene_id": f"scene-{number:02d}",
                        "narration": f"कथा {number}",
                        "visual_prompt": f"दृश्य {number}",
                        "duration_seconds": 120,
                    }
                    for number in range(1, 5)
                ]
            }
            plan_path = root / "scene-plan.json"
            plan_path.write_text(__import__("json").dumps(plan, ensure_ascii=False), encoding="utf-8")
            with patch.object(renderer, "ffmpeg_available", return_value=True), \
                 patch.object(renderer, "run"):
                renderer.render(scenes, root / "out", scene_plan_path=plan_path, min_minutes=8/60, max_minutes=1)
            import json
            report = json.loads((root / "out" / "render-report.json").read_text(encoding="utf-8"))
            self.assertEqual([row["duration_seconds"] for row in report["scenes"]], [120.0] * 4)

    def test_scene_plan_must_match_available_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            scenes.mkdir()
            (scenes / "scene-01.png").write_bytes(b"image placeholder")
            plan_path = root / "scene-plan.json"
            plan_path.write_text(__import__("json").dumps({
                "scenes": [{
                    "scene_id": "scene-02",
                    "narration": "कथा",
                    "visual_prompt": "दृश्य",
                    "duration_seconds": 120,
                }]
            }, ensure_ascii=False), encoding="utf-8")
            with patch.object(renderer, "ffmpeg_available", return_value=True):
                with self.assertRaisesRegex(ValueError, "do not match"):
                    renderer.render(scenes, root / "out", scene_plan_path=plan_path, min_minutes=2, max_minutes=10)

    def test_renderer_report_policy_is_private_review_only(self):
        source = Path(renderer.__file__).read_text(encoding="utf-8")
        self.assertIn('"upload_enabled": False', source)
        self.assertIn("No upload or publishing was performed.", source)


if __name__ == "__main__":
    unittest.main()
