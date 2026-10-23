import unittest

from scripts.comfyui_generate_assets import replace_tokens


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


if __name__ == "__main__":
    unittest.main()
