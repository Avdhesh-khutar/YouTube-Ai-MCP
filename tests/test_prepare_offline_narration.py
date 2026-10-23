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
                if "-w" in command:
                    Path(command[command.index("-w") + 1]).write_bytes(b"fake wav")
                else:
                    Path(command[-1]).write_bytes(b"joined wav")
                    concat_path = Path(command[command.index("-i") + 1])
                    concat_text = concat_path.read_text(encoding="utf-8")
                    self.assertIn("file '", concat_text)
                    self.assertNotIn("\\\\nfile", concat_text)
                return type("Result", (), {"returncode": 0, "stderr": ""})()
            with patch("scripts.prepare_offline_narration.shutil.which", side_effect=lambda name: "/usr/bin/" + name) as which_patch:
                with patch("scripts.prepare_offline_narration.subprocess.run", side_effect=fake_run):
                    audio, srt = prepare(plan_path, root / "out", 8, 8)
            self.assertTrue(audio.is_file())
            content = srt.read_text(encoding="utf-8")
            self.assertEqual(content.count("-->"), 4)
            self.assertIn("1\\\\n00:00:00,000", content)
            self.assertNotIn("\\\\n2\\\\n", content)
            self.assertIn("00:02:00,000 --> 00:04:00,000", content)


if __name__ == "__main__":
    unittest.main()
