import json
import unittest
from pathlib import Path


class CinematicWorkflowConfigSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = Path("config/cinematic-workflow.example.json")
        cls.config = json.loads(config_path.read_text(encoding="utf-8"))

    def test_youtube_upload_is_disabled_by_default(self):
        upload = self.config["workflow"]["youtube_upload"]
        self.assertFalse(upload["enabled"])
        self.assertEqual(upload["privacy_status"], "private")
        self.assertTrue(upload["require_owner_approval"])
        self.assertFalse(upload["allow_public_publish"])

    def test_external_generation_providers_are_not_preconfigured(self):
        workflow = self.config["workflow"]
        self.assertEqual(workflow["image_generation"]["provider"], "UNCONFIGURED")
        self.assertEqual(workflow["image_to_video"]["provider"], "UNCONFIGURED")
        self.assertEqual(workflow["voiceover"]["provider"], "UNCONFIGURED")

    def test_secrets_are_not_intended_for_commits_or_logs(self):
        security = self.config["security"]
        self.assertTrue(security["never_log_secrets"])
        self.assertTrue(security["never_commit_secrets"])
        self.assertTrue(security["read_secrets_from_environment_or_secret_manager_only"])


if __name__ == "__main__":
    unittest.main()
