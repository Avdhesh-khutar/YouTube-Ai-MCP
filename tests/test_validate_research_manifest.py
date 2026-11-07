import unittest

from scripts.validate_research_manifest import ManifestError, validate_manifest


class ResearchManifestTests(unittest.TestCase):
    def base_manifest(self):
        return {
            "sources": [{"id": "s1", "title": "Official report", "url": "https://example.org/report"}],
            "claims": [{"id": "c1", "text": "A sourced statement.", "source_ids": ["s1"]}],
        }

    def test_accepts_claim_linked_to_https_source(self):
        result = validate_manifest(self.base_manifest())
        self.assertTrue(result["valid"])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["verified_claim_count"], 0)

    def test_rejects_claim_without_source(self):
        data = self.base_manifest()
        data["claims"][0]["source_ids"] = []
        with self.assertRaisesRegex(ManifestError, "must cite at least one"):
            validate_manifest(data)

    def test_rejects_unknown_source_reference(self):
        data = self.base_manifest()
        data["claims"][0]["source_ids"] = ["missing"]
        with self.assertRaisesRegex(ManifestError, "unknown source"):
            validate_manifest(data)

    def test_rejects_http_source(self):
        data = self.base_manifest()
        data["sources"][0]["url"] = "http://example.org/report"
        with self.assertRaisesRegex(ManifestError, "HTTPS"):
            validate_manifest(data)

    def test_verified_claim_needs_verification_note(self):
        data = self.base_manifest()
        data["claims"][0]["status"] = "verified"
        with self.assertRaisesRegex(ManifestError, "verification_note"):
            validate_manifest(data)

    def test_verified_claim_with_note_is_counted(self):
        data = self.base_manifest()
        data["claims"][0].update(status="verified", verification_note="Checked against the cited report.")
        self.assertEqual(validate_manifest(data)["verified_claim_count"], 1)


if __name__ == "__main__":
    unittest.main()
