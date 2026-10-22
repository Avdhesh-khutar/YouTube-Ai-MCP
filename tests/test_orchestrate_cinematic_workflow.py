import json
import tempfile
import unittest
from pathlib import Path

from scripts.orchestrate_cinematic_workflow import WorkflowError, create_job, validate_config


class WorkflowOrchestratorTests(unittest.TestCase):
    def base_config(self):
        return {
            "language": "hi-IN",
            "target_duration_minutes": {"min": 8, "max": 10},
            "workflow": {"youtube_upload": {"enabled": True, "privacy_status": "private", "allow_public_publish": False}},
            "security": {"never_commit_secrets": True, "never_log_secrets": True},
        }

    def test_rejects_public_upload(self):
        config = self.base_config()
        config["workflow"]["youtube_upload"]["privacy_status"] = "public"
        with self.assertRaises(WorkflowError):
            validate_config(config)

    def test_rejects_public_publish_flag(self):
        config = self.base_config()
        config["workflow"]["youtube_upload"]["allow_public_publish"] = True
        with self.assertRaises(WorkflowError):
            validate_config(config)

    def test_creates_job_manifest_without_provider_calls(self):
        config = self.base_config()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            config_path = tmp / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            job = create_job("प्राचीन भारत के रहस्य", config_path, tmp / "jobs")
            manifest = json.loads((job / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["upload"]["privacy_status"], "private")
            self.assertFalse(manifest["upload"]["public_publish"])
            self.assertTrue((job / "NEXT_STEPS.md").exists())

    def test_rejects_too_short_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            config_path = tmp / "config.json"
            config_path.write_text(json.dumps(self.base_config()), encoding="utf-8")
            with self.assertRaises(WorkflowError):
                create_job("AI", config_path, tmp / "jobs")


if __name__ == "__main__":
    unittest.main()
