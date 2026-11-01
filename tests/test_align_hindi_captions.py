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

    def test_groups_word_timestamps_into_short_caption_lines(self):
        words = [
            SimpleNamespace(start=0.1, end=0.35, word=" नमस्ते"),
            SimpleNamespace(start=0.36, end=0.7, word=" दोस्तों"),
            SimpleNamespace(start=0.72, end=1.0, word=" आज"),
            SimpleNamespace(start=1.02, end=1.3, word=" हम"),
            SimpleNamespace(start=1.31, end=1.7, word=" कहानी"),
            SimpleNamespace(start=1.71, end=2.0, word=" सुनेंगे"),
            SimpleNamespace(start=2.01, end=2.3, word=" साथ"),
            SimpleNamespace(start=2.31, end=2.6, word=" में"),
        ]
        segments = [SimpleNamespace(start=0.1, end=2.6, text="नमस्ते दोस्तों आज हम कहानी सुनेंगे साथ में", words=words)]
        result = segments_to_srt(segments, max_words=4)
        self.assertEqual(result.count("-->"), 2)
        self.assertIn("00:00:00,100 --> 00:00:01,300", result)
        self.assertIn("नमस्ते दोस्तों आज हम", result)
        self.assertIn("00:00:01,310 --> 00:00:02,600", result)
        self.assertIn("कहानी सुनेंगे साथ में", result)

    def test_segment_only_recognizer_fallback_still_works(self):
        segments = [SimpleNamespace(start=0.0, end=1.5, text="केवल सेगमेंट टाइमिंग")]
        self.assertIn("केवल सेगमेंट टाइमिंग", segments_to_srt(segments))

    def test_missing_audio_fails_before_model_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, "not found"):
                transcribe_to_srt(Path(tmp) / "missing.wav", Path(tmp) / "captions.srt")


if __name__ == "__main__":
    unittest.main()
