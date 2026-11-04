import importlib.util
import json
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("inspect_hf_space_api", "scripts/inspect_hf_space_api.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class InspectHfSpaceApiTests(unittest.TestCase):
    def test_builds_metadata_url(self):
        self.assertEqual(
            module.space_openapi_url("owner/my_space"),
            "https://owner-my-space.hf.space/gradio_api/openapi.json",
        )

    def test_rejects_invalid_space_identifier(self):
        with self.assertRaisesRegex(ValueError, "owner/name"):
            module.space_openapi_url("https://example.com")

    def test_summarizes_endpoints_without_executing_them(self):
        result = module.summarize_schema({
            "openapi": "3.0.2",
            "info": {"title": "Demo"},
            "paths": {"/run": {"post": {"operationId": "run", "requestBody": {
                "content": {"application/json": {"schema": {"type": "object"}}}
            }}}},
        })
        self.assertEqual(result["endpoints"][0]["path"], "/run")
        self.assertEqual(result["endpoints"][0]["method"], "POST")
        self.assertEqual(result["endpoints"][0]["request_schema"], {"type": "object"})

    def test_rejects_missing_paths(self):
        with self.assertRaisesRegex(ValueError, "No OpenAPI paths"):
            module.summarize_schema({"openapi": "3.0.2", "paths": {}})

    def test_fetches_only_the_metadata_url(self):
        body = json.dumps({"paths": {"/predict": {"post": {"operationId": "predict"}}}}).encode()
        response = Mock(status=200)
        response.read.return_value = body
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(module, "urlopen", return_value=response) as open_url:
            result = module.fetch_schema("https://demo.hf.space/gradio_api/openapi.json")
        open_url.assert_called_once()
        self.assertEqual(result["endpoints"][0]["path"], "/predict")


if __name__ == "__main__":
    unittest.main()
