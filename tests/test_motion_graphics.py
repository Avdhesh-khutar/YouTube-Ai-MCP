import unittest

from scripts.motion_graphics import (
    build_title_overlay_filter,
    escape_drawtext,
    title_for_scene,
)


class MotionGraphicsTests(unittest.TestCase):
    def test_title_filter_animates_lower_third(self):
        result = build_title_overlay_filter("भारत की अनसुनी कहानी", 8.0)
        self.assertIn("drawbox=", result)
        self.assertIn("drawtext=text='भारत की अनसुनी कहानी'", result)
        self.assertIn("alpha='if(", result)
        self.assertIn("between(t,0,4.800)", result)

    def test_filter_escapes_option_delimiters_and_limits_length(self):
        result = escape_drawtext("A:B, C% [D] " + "x" * 120)
        self.assertIn(r"\:", result)
        self.assertIn(r"\,", result)
        self.assertIn(r"\%", result)
        self.assertLessEqual(len(result), 90)

    def test_scene_title_prefers_explicit_title_then_narration(self):
        self.assertEqual(title_for_scene({"title": "Intro"}, "Scene 1"), "Intro")
        self.assertEqual(
            title_for_scene({"narration": "यह एक छोटी कहानी है"}, "Scene 1"),
            "यह एक छोटी कहानी है",
        )
        self.assertEqual(title_for_scene({}, "Scene 1"), "Scene 1")

    def test_rejects_non_positive_duration(self):
        with self.assertRaises(ValueError):
            build_title_overlay_filter("Title", 0)


if __name__ == "__main__":
    unittest.main()
