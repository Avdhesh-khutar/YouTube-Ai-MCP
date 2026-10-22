import json
import unittest
from unittest.mock import patch

from scripts.generate_hindi_script_ollama import generate


def package():
    return {
        "title": "इतिहास",
        "description": "डॉक्यूमेंट्री",
        "narration": "भारत के इतिहास की यात्रा। " * 40,
        "scenes": [
            {
                "scene": i,
                "narration_excerpt": "इतिहास का एक दृश्य।",
                "image_prompt": f"Cinematic India scene {i}",
                "negative_prompt": "blurry",
                "duration_seconds": 30,
            }
            for i in range(1, 13)
        ],
    }


class LocalOllamaGeneratorTests(unittest.TestCase):
    def test_rejects_duration_outside_target_range(self):
        with self.assertRaises(ValueError):
            generate("भारत का इतिहास", "qwen2.5:3b", 12)

    @patch("scripts.generate_hindi_script_ollama.urllib.request.urlopen")
    def test_uses_local_ollama_and_marks_no_paid_api(self, mocked_open):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({"message": {"content": json.dumps(package(), ensure_ascii=False)}}).encode()

        mocked_open.return_value = Response()
        result = generate("भारत का इतिहास", "qwen2.5:3b", 9)
        request = mocked_open.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertFalse(result["paid_api_used"])
        self.assertEqual(result["provider"], "ollama-local")


if __name__ == "__main__":
    unittest.main()
