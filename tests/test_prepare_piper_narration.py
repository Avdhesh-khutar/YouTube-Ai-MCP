import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_piper_narration import prepare


class PiperHindiNarrationTests(unittest.TestCase):
    def _plan(self, root):
        path = root / "scene-plan.json"
        path.write_text(json.dumps({"scenes": [
            {"scene_id": f"scene-{i:02d}", "narration": f"हिंदी कथन {i}",
             "visual_prompt": f"दृश्य {i}", "duration_seconds": 120}
            for i in range(1, 5)
        ]}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_generates_scene_audio_and_srt_with_piper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = self._plan(root)
            model = root / "hi_IN-rohan-medium.onnx"
            config = root / "hi_IN-rohan-medium.onnx.json"
            model.write_bytes(b"model")
            config.write_text("{}", encoding="utf-8")
            def fake_run(command, capture_output, text, check, **kwargs):
                if command[0] == "/usr/bin/piper":
                    self.assertEqual(kwargs["input"], "हिंदी कथन " + str(len(piper_calls) + 1))
                    self.assertEqual(command[1:3], ["--model", str(model)])
                    self.assertNotIn("--config", command)
                    Path(command[command.index("--output_file") + 1]).write_bytes(b"piper wav")
                    piper_calls.append(command)
                elif command[0] == "/usr/bin/ffprobe":
                    return type("Result", (), {"returncode": 0, "stdout": "60.0", "stderr": ""})()
                elif "-f" in command and "concat" in command:
                    Path(command[-1]).write_bytes(b"joined wav")
                else:
                    Path(command[-1]).write_bytes(b"padded wav")
                return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            piper_calls = []
            with patch("scripts.prepare_piper_narration.shutil.which", side_effect=lambda name: "/usr/bin/" + name):
                with patch("scripts.prepare_piper_narration.subprocess.run", side_effect=fake_run):
                    audio, srt = prepare(plan, model, root / "out", 8, 8)
            self.assertTrue(audio.is_file())
            self.assertEqual(len(piper_calls), 4)
            content = srt.read_text(encoding="utf-8")
            self.assertEqual(content.count("-->"), 4)
            self.assertIn("00:06:00,000 --> 00:08:00,000", content)

    def test_missing_model_fails_before_external_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = self._plan(root)
            with patch("scripts.prepare_piper_narration.subprocess.run") as run:
                with self.assertRaisesRegex(FileNotFoundError, "Piper model not found"):
                    prepare(plan, root / "missing.onnx", root / "out")
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
