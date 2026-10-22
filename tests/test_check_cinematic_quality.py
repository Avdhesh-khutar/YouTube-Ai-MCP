import tempfile
import unittest
from pathlib import Path

from scripts.check_cinematic_quality import check


class CinematicQualityTests(unittest.TestCase):
    def test_missing_video_and_subtitles_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = check(root / "missing.mp4", root / "missing.srt")
            self.assertFalse(report["ready_for_owner_review"])
            self.assertFalse(report["upload_performed"])
            self.assertFalse(report["public_publish"])
            self.assertGreaterEqual(len(report["errors"]), 2)

    def test_valid_srt_is_detected_without_ffprobe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            subtitles = root / "captions.srt"
            video.write_bytes(b"test video placeholder")
            subtitles.write_text(
                "1\\n00:00:00,000 --> 00:00:02,000\\nनमस्ते दुनिया\\n",
                encoding="utf-8",
            )
            report = check(video, subtitles)
            self.assertEqual(report["checks"]["video_file"], "pass")
            self.assertEqual(report["checks"]["subtitles"], "pass")
            self.assertFalse(report["upload_performed"])

    def test_empty_subtitle_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            subtitles = root / "captions.srt"
            video.write_bytes(b"placeholder")
            subtitles.write_text("", encoding="utf-8")
            report = check(video, subtitles)
            self.assertFalse(report["ready_for_owner_review"])
            self.assertEqual(report["checks"]["subtitles"], "fail")


if __name__ == "__main__":
    unittest.main()
