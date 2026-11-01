import unittest
from unittest.mock import patch

from scripts.check_comfyui_endpoint import check_endpoint


class ComfyEndpointTests(unittest.TestCase):
    def test_rejects_plain_http_remote_endpoint(self):
        with self.assertRaises(ValueError):
            check_endpoint("http://example.com")

    def test_rejects_credentials_in_url(self):
        with self.assertRaises(ValueError):
            check_endpoint("https://user:password@example.com")

    @patch("scripts.check_comfyui_endpoint.urllib.request.urlopen")
    def test_reports_comfyui_compatible_endpoint(self, mocked_open):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"system": "ok"}'

        mocked_open.return_value = Response()
        result = check_endpoint("http://127.0.0.1:8188")
        self.assertTrue(result["reachable"])
        self.assertFalse(result["generation_submitted"])


if __name__ == "__main__":
    unittest.main()
