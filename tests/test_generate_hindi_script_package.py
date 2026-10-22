import unittest

from scripts.generate_hindi_script_package import validate_package


def sample_package(scene_count=12):
    return {
        "title": "प्राचीन भारत",
        "description": "एक डॉक्यूमेंट्री",
        "narration": "भारत के इतिहास की एक रोचक यात्रा। " * 40,
        "scenes": [
            {
                "scene": i,
                "narration_excerpt": "यह दृश्य इतिहास की एक झलक दिखाता है।",
                "image_prompt": f"Cinematic historical India scene {i}, 16:9",
                "negative_prompt": "blurry, low quality",
                "duration_seconds": 30,
            }
            for i in range(1, scene_count + 1)
        ],
    }


class HindiScriptPackageTests(unittest.TestCase):
    def test_validates_and_marks_package_for_fact_check(self):
        package = sample_package()
        validate_package(package, 9)
        self.assertEqual(package["language"], "hi-IN")
        self.assertEqual(package["target_duration_minutes"], 9)
        self.assertIn("needs_human", package["fact_check_status"])
        self.assertFalse(package["youtube_upload_performed"])

    def test_rejects_too_few_scenes(self):
        with self.assertRaises(ValueError):
            validate_package(sample_package(4), 9)

    def test_rejects_empty_image_prompt(self):
        package = sample_package()
        package["scenes"][0]["image_prompt"] = ""
        with self.assertRaises(ValueError):
            validate_package(package, 9)


if __name__ == "__main__":
    unittest.main()
