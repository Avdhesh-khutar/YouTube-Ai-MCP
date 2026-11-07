import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_offline_narration import prepare, timestamp


class OfflineNarrationTests(unittest.TestCase):
    def test_timestamp_formats_hours_minutes_seconds_and_milliseconds(self):
        self.assertEqual(timestamp(0), "00:00:00,000")
        self.assertEqual(timestamp(61.234), "00:01:01,234")
        self.assertEqual(timestamp(3661.999), "01:01:01,999")

    def test_writes_real_srt_blocks_and_ffmpeg_concat_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "scene-plan.json"
            plan_path.write_text(json.dumps({"scenes": [
                {"scene_id": f"scene-{i:02d}", "narration": f"हिंदी दृश्य {i}",
                 "visual_prompt": f"चित्र {i}", "duration_seconds": 120}
                for i in range(1, 5)
            ]}, ensure_ascii=False), encoding="utf-8")
            def fake_run(command, capture_output, text, check):
                if "ffprobe" in command[0]:
                    return type("Result", (), {"returncode": 0, "stdout": "60.0", "stderr": ""})()
                if "-w" in command:
                    Path(command[command.index("-w") + 1]).write_bytes(b"fake wav")
                elif "-f" in command and "concat" in command:
                    Path(command[-1]).write_bytes(b"joined wav")
                    concat_path = Path(command[command.index("-i") + 1])
                    concat_text = concat_path.read_text(encoding="utf-8")
                    self.assertIn("file '", concat_text)
                    self.assertIn("\nfile", concat_text)
                else:
                    self.assertIn("apad", command)
                    self.assertIn("-t", command)
                    Path(command[-1]).write_bytes(b"padded wav")
                return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            with patch("scripts.prepare_offline_narration.shutil.which", side_effect=lambda name: "/usr/bin/" + name) as which_patch:
                with patch("scripts.prepare_offline_narration.subprocess.run", side_effect=fake_run):
                    audio, srt = prepare(plan_path, root / "out", 8, 8)
            self.assertTrue(audio.is_file())
            content = srt.read_text(encoding="utf-8")
            self.assertEqual(content.count("-->"), 4)
            self.assertIn("1\n00:00:00,000", content)
            self.assertIn("\n\n2\n", content)
            self.assertIn("00:02:00,000 --> 00:04:00,000", content)

    def test_rejects_scenes_with_excessive_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "scene-plan.json"
            plan_path.write_text(json.dumps({"scenes": [
                {"scene_id": f"scene-{i:02d}", "narration": "बहुत छोटा वाक्य",
                 "visual_prompt": "चित्र", "duration_seconds": 120}
                for i in range(1, 5)
            ]}, ensure_ascii=False), encoding="utf-8")
            def fake_run(command, capture_output, text, check):
                if "-w" in command:
                    Path(command[command.index("-w") + 1]).write_bytes(b"fake wav")
                    return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                return type("Result", (), {"returncode": 0, "stdout": "10.0", "stderr": ""})()
            with patch("scripts.prepare_offline_narration.shutil.which", side_effect=lambda name: "/usr/bin/" + name):
                with patch("scripts.prepare_offline_narration.subprocess.run", side_effect=fake_run):
                    with self.assertRaisesRegex(ValueError, "excessive|only 10.0s of speech|minimum is"):
                        prepare(plan_path, root / "out", 8, 8, min_speech_coverage=0.20)

    def test_rejects_narration_longer_than_scene_instead_of_truncating_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "scene-plan.json"
            plan_path.write_text(json.dumps({"scenes": [
                {"scene_id": f"scene-{i:02d}", "narration": "लंबा हिंदी कथन",
                 "visual_prompt": "चित्र", "duration_seconds": 120}
                for i in range(1, 5)
            ]}, ensure_ascii=False), encoding="utf-8")
            def fake_run(command, capture_output, text, check):
                if "-w" in command:
                    Path(command[command.index("-w") + 1]).write_bytes(b"fake wav")
                    return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
                return type("Result", (), {"returncode": 0, "stdout": "130.0", "stderr": ""})()
            with patch("scripts.prepare_offline_narration.shutil.which", side_effect=lambda name: "/usr/bin/" + name):
                with patch("scripts.prepare_offline_narration.subprocess.run", side_effect=fake_run):
                    with self.assertRaisesRegex(ValueError, "audio would be cut off"):
                        prepare(plan_path, root / "out", 8, 8, min_speech_coverage=0.20)

if __name__ == "__main__":
    unittest.main()
