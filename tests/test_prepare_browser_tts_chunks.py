import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("prepare_browser_tts_chunks", "scripts/prepare_browser_tts_chunks.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class BrowserTTSChunkTests(unittest.TestCase):
    def test_chunks_respect_limit_and_keep_sentence_text(self):
        text = ("यह पहला वाक्य है। " * 30) + "यह अंतिम वाक्य है।"
        chunks = module.chunk_text(text, 120)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks))
        self.assertEqual(" ".join(chunks).replace("  ", " "), text.strip())

    def test_long_sentence_splits_on_word_boundaries(self):
        text = " ".join(["शब्द"] * 80)
        chunks = module.chunk_text(text, 120)
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks))
        self.assertEqual(" ".join(chunks), text)

    def test_rejects_empty_text_and_too_small_limit(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            module.chunk_text("   ")
        with self.assertRaisesRegex(ValueError, "at least 100"):
            module.chunk_text("हिंदी", 50)

    def test_prepare_writes_manifest_and_numbered_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "script.txt"
            source.write_text("पहला वाक्य। दूसरा वाक्य।", encoding="utf-8")
            manifest_path = module.prepare(source, root / "out", 100)
            self.assertTrue((root / "out" / "chunk-001.txt").is_file())
            manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "text_chunks_prepared_audio_not_generated")
            self.assertEqual(manifest["chunks"][0]["expected_audio_file"], "chunk-001.wav")


if __name__ == "__main__":
    unittest.main()
