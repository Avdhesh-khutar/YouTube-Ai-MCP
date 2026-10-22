import unittest

from scripts.prepare_offline_narration import timestamp


class OfflineNarrationTests(unittest.TestCase):
    def test_timestamp_formats_hours_minutes_seconds_and_milliseconds(self):
        self.assertEqual(timestamp(0), "00:00:00,000")
        self.assertEqual(timestamp(61.234), "00:01:01,234")
        self.assertEqual(timestamp(3661.999), "01:01:01,999")


if __name__ == "__main__":
    unittest.main()
