import importlib
import os
import tempfile
import unittest
from unittest.mock import patch


class RemoteJobsAPITestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["JOBS_DATABASE_FILE"] = f"{self.temp_dir.name}/jobs.json"
        os.environ["REFRESH_ON_STARTUP"] = "false"
        os.environ["ENABLE_BACKGROUND_REFRESH"] = "false"

        import server

        self.server = importlib.reload(server)
        self.client = self.server.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("JOBS_DATABASE_FILE", None)
        os.environ.pop("REFRESH_ON_STARTUP", None)
        os.environ.pop("ENABLE_BACKGROUND_REFRESH", None)

    def test_refresh_normalizes_and_serves_jobs(self):
        remotive_job = {
            "title": "Senior Python Developer",
            "company_name": "RemoteCo",
            "candidate_required_location": "LATAM",
            "category": "Software Development",
            "tags": ["Python", "Flask"],
            "salary": "$5000 - $9000",
            "description": "<p>Build APIs</p>",
            "url": "https://remotive.com/remote-jobs/software-dev/senior-python",
            "publication_date": "2026-06-01T12:00:00Z",
        }
        remoteok_job = {
            "position": "React Engineer",
            "company": "Frontend Labs",
            "location": "Worldwide",
            "tags": ["React", "TypeScript"],
            "description": "Build UI",
            "url": "https://remoteok.com/remote-jobs/react-engineer",
            "epoch": 1780315200,
        }

        with patch.dict(
            self.server.SOURCE_FETCHERS,
            {
                "remotive": lambda: [self.server.normalize_job(remotive_job, "remotive")],
                "remoteok": lambda: [self.server.normalize_job(remoteok_job, "remoteok")],
            },
        ):
            result = self.server.refresh_jobs()

        self.assertEqual(result["status"], "ok")

        response = self.client.get("/jobs?q=python&location=latam&include_description=true")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["metadata"]["total"], 1)
        self.assertEqual(payload["jobs"][0]["company"], "RemoteCo")
        self.assertEqual(payload["jobs"][0]["description"], "Build APIs")

    def test_job_detail_returns_404_for_unknown_id(self):
        response = self.client.get("/jobs/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_public_refresh_is_disabled_by_default(self):
        response = self.client.post("/refresh")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
