import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.align_hindi_captions import segments_to_srt, transcribe_to_srt


class SpeechTimedHindiCaptionTests(unittest.TestCase):
    def test_converts_audio_timestamped_segments_to_srt(self):
        segments = [
            SimpleNamespace(start=0.15, end=1.8, text=" नमस्कार दोस्तों "),
            SimpleNamespace(start=2.0, end=3.25, text="आज की कहानी"),
        ]
        result = segments_to_srt(segments)
        self.assertIn("00:00:00,150 --> 00:00:01,800", result)
        self.assertIn("नमस्कार दोस्तों", result)
        self.assertIn("00:00:02,000 --> 00:00:03,250", result)
        self.assertEqual(result.count("-->"), 2)

    def test_skips_empty_and_invalid_segments_and_rejects_empty_output(self):
        segments = [
            SimpleNamespace(start=0, end=1, text=""),
            SimpleNamespace(start=2, end=1, text="invalid"),
        ]
        with self.assertRaisesRegex(ValueError, "no usable"):
            segments_to_srt(segments)

    def test_clamps_overlapping_segments_to_previous_end(self):
        segments = [
            SimpleNamespace(start=0, end=2, text="पहला वाक्य"),
            SimpleNamespace(start=1.5, end=3, text="दूसरा वाक्य"),
        ]
        result = segments_to_srt(segments)
        self.assertIn("00:00:02,000 --> 00:00:03,000", result)

    def test_missing_audio_fails_before_model_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, "not found"):
                transcribe_to_srt(Path(tmp) / "missing.wav", Path(tmp) / "captions.srt")


if __name__ == "__main__":
    unittest.main()
