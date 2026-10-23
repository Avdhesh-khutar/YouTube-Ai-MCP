import unittest

from pathlib import Path

from scripts.comfyui_generate_assets import replace_tokens, validate_prompts, validate_output_bytes


class ComfyUITokenReplacementTests(unittest.TestCase):
    def test_replaces_tokens_recursively_in_nested_workflow(self):
        workflow = {
            "1": {
                "inputs": {
                    "text": "__POSITIVE_PROMPT__",
                    "negative": "__NEGATIVE_PROMPT__",
                    "filename_prefix": "__OUTPUT_PREFIX__",
                }
            },
            "2": ["prefix __POSITIVE_PROMPT__", {"image": "__INPUT_IMAGE__"}],
        }
        result = replace_tokens(workflow, {
            "__POSITIVE_PROMPT__": "Hindi history scene",
            "__NEGATIVE_PROMPT__": "blurry",
            "__OUTPUT_PREFIX__": "review/scene-01",
            "__INPUT_IMAGE__": "scene-01.png",
        })
        self.assertEqual(result["1"]["inputs"]["text"], "Hindi history scene")
        self.assertEqual(result["1"]["inputs"]["negative"], "blurry")
        self.assertEqual(result["1"]["inputs"]["filename_prefix"], "review/scene-01")
        self.assertEqual(result["2"][0], "prefix Hindi history scene")
        self.assertEqual(result["2"][1]["image"], "scene-01.png")

    def test_does_not_mutate_original_workflow(self):
        workflow = {"node": {"text": "__POSITIVE_PROMPT__"}}
        result = replace_tokens(workflow, {"__POSITIVE_PROMPT__": "hello"})
        self.assertEqual(workflow["node"]["text"], "__POSITIVE_PROMPT__")
        self.assertEqual(result["node"]["text"], "hello")

    def test_preserves_non_string_values(self):
        workflow = {"steps": 4, "enabled": True, "empty": None}
        result = replace_tokens(workflow, {"__POSITIVE_PROMPT__": "hello"})
        self.assertEqual(result, workflow)


    def test_validates_scene_prompt_records(self):
        prompts = [
            {"scene": 1, "image_prompt": "A historic fort", "negative_prompt": "blurry"},
            {"scene": 3, "image_prompt": "A river at sunrise"},
        ]
        self.assertEqual(validate_prompts(prompts), prompts)

    def test_rejects_duplicate_scene_numbers(self):
        with self.assertRaisesRegex(ValueError, "Duplicate scene number"):
            validate_prompts([
                {"scene": 1, "image_prompt": "first"},
                {"scene": 1, "image_prompt": "second"},
            ])

    def test_rejects_missing_prompt_and_invalid_scene_number(self):
        with self.assertRaisesRegex(ValueError, "image_prompt"):
            validate_prompts([{"scene": 1, "image_prompt": " "}])
        with self.assertRaisesRegex(ValueError, "positive integer"):
            validate_prompts([{"scene": True, "image_prompt": "scene"}])

    def test_rejects_empty_or_non_list_prompt_data(self):
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            validate_prompts([])
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            validate_prompts({"scene": 1, "image_prompt": "scene"})


    def test_rejects_empty_generated_output(self):
        with self.assertRaisesRegex(RuntimeError, "empty output"):
            validate_output_bytes(Path("scene-01.png"), b"")

    def test_rejects_image_bytes_with_wrong_extension(self):
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            validate_output_bytes(Path("scene-01.png"), b"not a png")

    def test_accepts_png_and_mp4_signatures(self):
        validate_output_bytes(Path("scene-01.png"), b"\x89PNG\r\n\x1a\nrest")
        validate_output_bytes(Path("scene-01.mp4"), b"\x00\x00\x00\x18ftypisomrest")


if __name__ == "__main__":
    unittest.main()
