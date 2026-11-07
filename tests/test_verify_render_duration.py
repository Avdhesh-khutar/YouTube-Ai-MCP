import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from scripts import verify_render_duration as gate


class RenderDurationGateTests(unittest.TestCase):
    def test_accepts_actual_runtime_with_video_and_audio(self):
        payload = {
            "format": {"duration": "540.25"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "final.mp4"
            video.write_bytes(b"placeholder")
            with patch.object(gate.shutil, "which", return_value="/usr/bin/ffprobe"), patch.object(
                gate.subprocess, "run", return_value=Mock(returncode=0, stdout=json.dumps(payload), stderr="")
            ):
                result = gate.verify(video, require_audio=True)
        self.assertEqual(result["duration_seconds"], 540.25)
        self.assertTrue(result["has_audio"])
        self.assertEqual(result["video_codec"], "h264")

    def test_rejects_short_clip_even_if_file_is_valid(self):
        payload = {
            "format": {"duration": "4.0"},
            "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "short.mp4"
            video.write_bytes(b"placeholder")
            with patch.object(gate.shutil, "which", return_value="/usr/bin/ffprobe"), patch.object(
                gate.subprocess, "run", return_value=Mock(returncode=0, stdout=json.dumps(payload), stderr="")
            ):
                with self.assertRaisesRegex(gate.MediaCheckError, "outside the allowed"):
                    gate.verify(video)

    def test_rejects_missing_audio_when_required(self):
        payload = {
            "format": {"duration": "540"},
            "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "silent.mp4"
            video.write_bytes(b"placeholder")
            with patch.object(gate.shutil, "which", return_value="/usr/bin/ffprobe"), patch.object(
                gate.subprocess, "run", return_value=Mock(returncode=0, stdout=json.dumps(payload), stderr="")
            ):
                with self.assertRaisesRegex(gate.MediaCheckError, "Audio is required"):
                    gate.verify(video, require_audio=True)

    def test_rejects_invalid_duration_bounds(self):
        with self.assertRaisesRegex(ValueError, "duration bounds"):
            gate.verify(Path("unused.mp4"), min_seconds=600, max_seconds=480)


if __name__ == "__main__":
    unittest.main()
