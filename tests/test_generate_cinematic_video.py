import contextlib
import io
import json
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

    def _write_eight_minute_plan(self, root: Path, scenes: Path) -> Path:
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
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        return plan_path

    def test_report_separates_planned_and_actual_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            plan_path = self._write_eight_minute_plan(root, scenes)
            with patch.object(renderer, "ffmpeg_available", return_value=True), \
                 patch.object(renderer, "run"), \
                 patch.object(renderer, "probe_duration", return_value=480.0):
                renderer.render(scenes, root / "out", scene_plan_path=plan_path, min_minutes=8, max_minutes=10)
            report = json.loads((root / "out" / "render-report.json").read_text(encoding="utf-8"))
            self.assertEqual([row["planned_duration_seconds"] for row in report["scenes"]], [120.0] * 4)
            self.assertEqual(report["planned_duration_seconds"], 480.0)
            self.assertEqual(report["actual_duration_seconds"], 480.0)
            self.assertEqual(report["duration_difference_seconds"], 0.0)

    def test_rejects_final_video_shorter_than_validated_scene_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            plan_path = self._write_eight_minute_plan(root, scenes)
            with patch.object(renderer, "ffmpeg_available", return_value=True), \
                 patch.object(renderer, "run"), \
                 patch.object(renderer, "probe_duration", return_value=478.9):
                with self.assertRaisesRegex(RuntimeError, "expected 480–600s"):
                    renderer.render(scenes, root / "out", scene_plan_path=plan_path,
                                    min_minutes=8, max_minutes=10)

    def test_rejects_motion_clip_shorter_than_planned_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            plan_path = self._write_eight_minute_plan(root, scenes)
            (scenes / "scene-01.mp4").write_bytes(b"short clip placeholder")
            with patch.object(renderer, "ffmpeg_available", return_value=True), \
                 patch.object(renderer, "probe_duration", return_value=3.5), \
                 patch.object(renderer, "run") as run_mock:
                with self.assertRaisesRegex(RuntimeError, "only 3.50s"):
                    renderer.render(scenes, root / "out", scene_plan_path=plan_path, min_minutes=8, max_minutes=10)
                run_mock.assert_not_called()

    def test_multiple_short_motion_clips_fill_one_long_scene_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            plan_path = self._write_eight_minute_plan(root, scenes)
            first = scenes / "scene-01-clip-002.mp4"
            second = scenes / "scene-01-clip-010.mp4"
            first.write_bytes(b"clip one")
            second.write_bytes(b"clip two")
            with patch.object(renderer, "ffmpeg_available", return_value=True), \
                 patch.object(renderer, "probe_duration", side_effect=[60.0, 60.0, 480.0]), \
                 patch.object(renderer, "run") as run_mock:
                renderer.render(scenes, root / "out", scene_plan_path=plan_path,
                                min_minutes=8, max_minutes=10)
            report = json.loads((root / "out" / "render-report.json").read_text(encoding="utf-8"))
            row = report["scenes"][0]
            self.assertEqual(row["motion"], "image-to-video clip sequence")
            self.assertEqual([clip["file"] for clip in row["source_clips"]],
                             ["scene-01-clip-002.mp4", "scene-01-clip-010.mp4"])
            self.assertEqual([clip["used_duration_seconds"] for clip in row["source_clips"]],
                             [60.0, 60.0])
            self.assertEqual(row["source_clip_duration_seconds"], 120.0)
            commands = [call.args[0] for call in run_mock.call_args_list]
            self.assertTrue(any(str(first) in command for command in commands))
            self.assertTrue(any(str(second) in command for command in commands))

    def test_rejects_numbered_motion_sequence_with_insufficient_total_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            plan_path = self._write_eight_minute_plan(root, scenes)
            (scenes / "scene-01-clip-002.mp4").write_bytes(b"clip two")
            (scenes / "scene-01-clip-010.mp4").write_bytes(b"clip ten")
            with patch.object(renderer, "ffmpeg_available", return_value=True), \
                 patch.object(renderer, "probe_duration", side_effect=[60.0, 30.0]), \
                 patch.object(renderer, "run") as run_mock:
                with self.assertRaisesRegex(RuntimeError, "provides only 90.00s"):
                    renderer.render(scenes, root / "out", scene_plan_path=plan_path,
                                    min_minutes=8, max_minutes=10)
                run_mock.assert_not_called()

    def test_scene_plan_must_match_available_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            scenes.mkdir()
            (scenes / "scene-01.png").write_bytes(b"image placeholder")
            plan_path = root / "scene-plan.json"
            plan_path.write_text(json.dumps({
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

    def test_optional_background_music_is_mixed_below_narration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenes = root / "scenes"
            plan_path = self._write_eight_minute_plan(root, scenes)
            (scenes / "voiceover.wav").write_bytes(b"voice placeholder")
            (scenes / "background-music.wav").write_bytes(b"music placeholder")
            with patch.object(renderer, "ffmpeg_available", return_value=True), \
                 patch.object(renderer, "run") as run_mock, \
                 patch.object(renderer, "probe_duration", return_value=480.0):
                renderer.render(scenes, root / "out", scene_plan_path=plan_path,
                                min_minutes=8, max_minutes=10)
            final_command = next(
                call.args[0] for call in run_mock.call_args_list
                if str(root / "out" / "cinematic-video.mp4") in call.args[0]
            )
            self.assertIn("-filter_complex", final_command)
            filter_text = final_command[final_command.index("-filter_complex") + 1]
            self.assertIn("amix=inputs=2:duration=first", filter_text)
            self.assertIn("volume=0.12", filter_text)
            self.assertIn("background-music.wav", final_command)
            report = json.loads((root / "out" / "render-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["background_music"], "background-music.wav")
            self.assertEqual(report["background_music_gain"], 0.12)

    def test_renderer_report_policy_is_private_review_only(self):
        source = Path(renderer.__file__).read_text(encoding="utf-8")
        self.assertIn('"upload_enabled": False', source)
        self.assertIn("No upload or publishing was performed.", source)


if __name__ == "__main__":
    unittest.main()
