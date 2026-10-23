import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("hf_space_i2v", "scripts/hf_space_i2v.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class HfSpaceI2VTests(unittest.TestCase):
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

    def test_accepts_mp4_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "clip.mp4"
            video.write_bytes(b"\x00\x00\x00\x18ftyp" + b"mock-video-data")
            module.validate_video(video)

    def test_resolves_prompt_and_duration_placeholders(self):
        self.assertEqual(
            module.resolve_args(["__PROMPT__", "__DURATION__", 7], Path("image.png"), "gentle motion", 4),
            ["gentle motion", 4, 7],
        )


if __name__ == "__main__":
    unittest.main()
