import unittest

from scripts.validate_scene_plan import ScenePlanError, validate_scene_plan


class ScenePlanValidationTests(unittest.TestCase):
    def make_plan(self, durations=None):
        durations = durations or [120] * 4
        return {
            "scenes": [
                {
                    "scene_id": f"scene-{index}",
                    "narration": f"Narration for scene {index}",
                    "visual_prompt": f"Visual for scene {index}",
                    "duration_seconds": duration,
                }
                for index, duration in enumerate(durations, start=1)
            ]
        }

    def test_accepts_scene_plan_within_duration_range(self):
        result = validate_scene_plan(self.make_plan([120, 120, 120, 120]))
        self.assertTrue(result["valid"])
        self.assertEqual(result["scene_count"], 4)
        self.assertEqual(result["total_duration_seconds"], 480)

    def test_rejects_empty_scene_list(self):
        with self.assertRaisesRegex(ScenePlanError, "non-empty list"):
            validate_scene_plan({"scenes": []})

    def test_rejects_duplicate_scene_ids(self):
        plan = self.make_plan([240, 240])
        plan["scenes"][1]["scene_id"] = plan["scenes"][0]["scene_id"]
        with self.assertRaisesRegex(ScenePlanError, "duplicate scene_id"):
            validate_scene_plan(plan)

    def test_rejects_missing_visual_prompt(self):
        plan = self.make_plan([240, 240])
        plan["scenes"][0]["visual_prompt"] = " "
        with self.assertRaisesRegex(ScenePlanError, "visual_prompt"):
            validate_scene_plan(plan)

    def test_rejects_invalid_scene_duration(self):
        plan = self.make_plan([240, 240])
        plan["scenes"][0]["duration_seconds"] = 1
        with self.assertRaisesRegex(ScenePlanError, "whole number"):
            validate_scene_plan(plan)

    def test_rejects_plan_shorter_than_requested_video(self):
        with self.assertRaisesRegex(ScenePlanError, "expected 480-600s"):
            validate_scene_plan(self.make_plan([60, 60]), min_minutes=8, max_minutes=10)


if __name__ == "__main__":
    unittest.main()
