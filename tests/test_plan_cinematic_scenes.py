import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.plan_cinematic_scenes import main
from scripts.validate_scene_plan import validate_scene_plan


class CinematicScenePlannerTests(unittest.TestCase):
    def test_writes_prompt_list_and_validated_duration_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "script.txt"
            script.write_text(
                "यह पहला दृश्य है। यह दूसरा दृश्य है। यह तीसरा दृश्य है। "
                "यह चौथा दृश्य है। " * 12,
                encoding="utf-8",
            )
            output = root / "out"
            with patch("sys.argv", [
                "plan_cinematic_scenes.py", "--script", str(script),
                "--output", str(output), "--max-scenes", "4",
                "--target-minutes", "8",
            ]):
                self.assertEqual(main(), 0)

            prompts = json.loads((output / "scene-prompts.json").read_text(encoding="utf-8"))
            plan = json.loads((output / "scene-plan.json").read_text(encoding="utf-8"))
            self.assertTrue(prompts)
            self.assertTrue(all("image_prompt" in item for item in prompts))
            report = validate_scene_plan(plan, 8, 8)
            self.assertEqual(report["total_duration_seconds"], 480)
            self.assertEqual(len(plan["scenes"]), len(prompts))
            self.assertTrue((output / "scene-prompts.md").exists())


if __name__ == "__main__":
    unittest.main()
