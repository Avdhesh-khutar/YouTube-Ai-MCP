import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.check_cinematic_quality import check, validate_srt


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
                "1\n00:00:00,000 --> 00:00:02,000\nनमस्ते दुनिया\n",
                encoding="utf-8",
            )
            report = check(video, subtitles)
            self.assertEqual(report["checks"]["video_file"], "pass")
            self.assertEqual(report["checks"]["subtitles"], "pass")
            self.assertFalse(report["upload_performed"])

    def test_srt_rejects_reversed_timestamp(self):
        count, end, errors = validate_srt(
            "1\n00:00:03,000 --> 00:00:01,000\nगलत समय\n"
        )
        self.assertEqual(count, 1)
        self.assertTrue(errors)


    def test_srt_rejects_overlapping_caption_intervals(self):
        count, end, errors = validate_srt(
            "1\n00:00:00,000 --> 00:00:03,000\nपहला कैप्शन\n\n"
            "2\n00:00:02,500 --> 00:00:04,000\nदूसरा कैप्शन\n"
        )
        self.assertEqual(count, 2)
        self.assertEqual(end, 4.0)
        self.assertTrue(any("overlaps the previous caption" in error for error in errors))

    def test_srt_reports_caption_end_time(self):
        count, end, errors = validate_srt(
            "1\n00:00:00,000 --> 00:00:02,500\nनमस्ते\n\n"
            "2\n00:00:02,500 --> 00:00:04,000\nदुनिया\n"
        )
        self.assertEqual(count, 2)
        self.assertEqual(end, 4.0)
        self.assertEqual(errors, [])


    def test_rejects_subtitles_that_extend_beyond_video_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            subtitles = root / "captions.srt"
            video.write_bytes(b"test video placeholder")
            subtitles.write_text(
                "1\n00:00:00,000 --> 00:00:12,000\n字幕文本\n",
                encoding="utf-8",
            )
            with patch("scripts.check_cinematic_quality.probe", return_value={
                "format": {"duration": "10"},
                "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
            }):
                report = check(video, subtitles, min_minutes=0.1, max_minutes=1)
            self.assertFalse(report["ready_for_owner_review"])
            self.assertTrue(any("Subtitles end at" in error for error in report["errors"]))

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


    def test_quality_gate_rejects_video_below_720p(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            subtitles = root / "captions.srt"
            video.write_bytes(b"video placeholder")
            subtitles.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\nनमस्ते दुनिया\n",
                encoding="utf-8",
            )
            metadata = {
                "format": {"duration": "4"},
                "streams": [
                    {"codec_type": "video", "width": 640, "height": 360},
                    {"codec_type": "audio"},
                ],
            }
            with patch("scripts.check_cinematic_quality.probe", return_value=metadata):
                report = check(video, subtitles, min_minutes=0.05, max_minutes=1)
            self.assertFalse(report["ready_for_owner_review"])
            self.assertEqual(report["checks"]["resolution"], "fail")
            self.assertTrue(any("below the 1280x720 minimum" in error for error in report["errors"]))

    def test_quality_gate_accepts_exact_720p_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            subtitles = root / "captions.srt"
            video.write_bytes(b"video placeholder")
            subtitles.write_text(
                "1\n00:00:00,000 --> 00:00:02,000\nनमस्ते दुनिया\n",
                encoding="utf-8",
            )
            metadata = {
                "format": {"duration": "4"},
                "streams": [
                    {"codec_type": "video", "width": 1280, "height": 720},
                    {"codec_type": "audio"},
                ],
            }
            with patch("scripts.check_cinematic_quality.probe", return_value=metadata):
                report = check(video, subtitles, min_minutes=0.05, max_minutes=1)
            self.assertTrue(report["ready_for_owner_review"], report["errors"])
            self.assertEqual(report["checks"]["resolution"], "pass")


if __name__ == "__main__":
    unittest.main()
