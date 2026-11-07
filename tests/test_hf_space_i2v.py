import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

SPEC = importlib.util.spec_from_file_location("hf_space_i2v", "scripts/hf_space_i2v.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class HfSpaceI2VTests(unittest.TestCase):
    def test_ltx_handler1_requires_exact_positional_schema(self):
        args = [None] * 17
        args[0] = "__PROMPT__"
        args[8] = "__IMAGE__"
        module.validate_endpoint_args("/handler_1", args)

    def test_ltx_handler1_rejects_wrong_image_position(self):
        args = [None] * 17
        args[0] = "__PROMPT__"
        with self.assertRaisesRegex(ValueError, "input 8"):
            module.validate_endpoint_args("/handler_1", args)

    def test_ltx_handler1_rejects_wrong_argument_count(self):
        with self.assertRaisesRegex(ValueError, "exactly 17"):
            module.validate_endpoint_args("/handler_1", [])

    def test_finds_video_in_nested_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "clip.mp4"
            video.write_bytes(b"\x00\x00\x00\x18ftyp" + b"mock-video-data")
            result = {"result": [{"video": str(video)}]}
            self.assertEqual(module.find_video_path(result), video)

    def test_does_not_treat_remote_url_as_local_video(self):
        self.assertIsNone(module.find_video_path("https://example.org/clip.mp4"))

    def test_rejects_empty_or_too_small_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "empty.mp4"
            video.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "missing or empty"):
                module.validate_video(video)

    def test_rejects_unknown_video_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "not-video.mp4"
            video.write_bytes(b"not a real video file at all")
            with self.assertRaisesRegex(ValueError, "signature"):
                module.validate_video(video)

    def test_rejects_non_video_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "image.png"
            image.write_bytes(b"\x00\x00\x00\x18ftyp" + b"mock-video-data")
            with self.assertRaisesRegex(ValueError, "recognized video extension"):
                module.validate_video(image)

    def test_require_playable_checks_ffprobe_video_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "clip.mp4"
            video.write_bytes(b"\x00\x00\x00\x18ftyp" + b"mock-video-data")
            completed = Mock(stdout=json.dumps({"streams": [{"codec_name": "h264", "width": 1280, "height": 720}]}), stderr="")
            with patch.object(module.subprocess, "run", return_value=completed) as run:
                module.validate_video(video, require_playable=True)
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0][0], "ffprobe")

    def test_rejects_file_without_video_stream_even_with_mp4_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "clip.mp4"
            video.write_bytes(b"\x00\x00\x00\x18ftyp" + b"mock-video-data")
            completed = Mock(stdout=json.dumps({"streams": []}), stderr="")
            with patch.object(module.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(ValueError, "no readable video stream"):
                    module.validate_video(video, require_playable=True)

    def test_resolves_prompt_and_duration_placeholders(self):
        self.assertEqual(
            module.resolve_args(["__PROMPT__", "__DURATION__", 7], Path("image.png"), "gentle motion", 4),
            ["gentle motion", 4, 7],
        )


if __name__ == "__main__":
    unittest.main()
