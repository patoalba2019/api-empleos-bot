import importlib
import os
import tempfile
import unittest
from unittest.mock import patch

import requests


class RemoteJobsAPITestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["JOBS_DATABASE_FILE"] = f"{self.temp_dir.name}/jobs.json"
        os.environ["REFRESH_ON_STARTUP"] = "false"
        os.environ["ENABLE_BACKGROUND_REFRESH"] = "false"
        os.environ["ENABLED_SOURCES"] = "jobicy,himalayas"
        os.environ["REQUIRE_PAID_GATEWAY"] = "false"

        import server

        self.server = importlib.reload(server)
        self.client = self.server.app.test_client()
        with self.server.cache_lock:
            self.server.cache["metadata"]["last_refresh_attempt_at"] = self.server.now_iso()

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("JOBS_DATABASE_FILE", None)
        os.environ.pop("REFRESH_ON_STARTUP", None)
        os.environ.pop("ENABLE_BACKGROUND_REFRESH", None)
        os.environ.pop("ENABLED_SOURCES", None)
        os.environ.pop("REQUIRE_PAID_GATEWAY", None)
        os.environ.pop("PAID_GATEWAY_SECRETS", None)
        os.environ.pop("PAID_GATEWAY_SECRET", None)
        os.environ.pop("PAID_GATEWAY_SECRET_HASHES", None)

    def test_refresh_normalizes_and_serves_jobs(self):
        himalayas_job = {
            "title": "Senior Python Developer",
            "companyName": "RemoteCo",
            "locationRestrictions": [{"name": "Argentina", "alpha2": "AR"}],
            "categories": ["Software Development"],
            "parentCategories": ["Engineering"],
            "seniority": ["Senior"],
            "employmentType": "Full Time",
            "minSalary": 5000,
            "maxSalary": 9000,
            "currency": "USD",
            "description": "<p>Build APIs</p>",
            "applicationLink": "https://himalayas.app/jobs/senior-python",
            "pubDate": "2026-06-01T12:00:00Z",
        }
        jobicy_job = {
            "jobTitle": "React Engineer",
            "companyName": "Frontend Labs",
            "jobGeo": "Worldwide",
            "jobIndustry": ["Software Engineering"],
            "jobType": ["Full-Time"],
            "jobLevel": "Senior",
            "jobDescription": "Build UI",
            "url": "https://jobicy.com/jobs/react-engineer",
            "pubDate": "2026-06-01T12:00:00Z",
        }

        with patch.dict(
            self.server.SOURCE_FETCHERS,
            {
                "jobicy": lambda: [self.server.normalize_job(jobicy_job, "jobicy")],
                "himalayas": lambda: [self.server.normalize_job(himalayas_job, "himalayas")],
            },
        ):
            result = self.server.refresh_jobs()

        self.assertEqual(result["status"], "ok")

        response = self.client.get("/jobs?q=python&location=argentina&include_description=true")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["metadata"]["total"], 1)
        self.assertEqual(payload["jobs"][0]["company"], "RemoteCo")
        self.assertEqual(payload["jobs"][0]["description"], "Build APIs")
        self.assertEqual(payload["jobs"][0]["salary"], "USD 5000 - 9000")

    def test_job_detail_returns_404_for_unknown_id(self):
        response = self.client.get("/jobs/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_public_refresh_is_disabled_by_default(self):
        response = self.client.post("/refresh")
        self.assertEqual(response.status_code, 403)

    def test_repairs_mojibake_in_locations(self):
        self.assertEqual(
            self.server.clean_location("Ø§Ù„Ù…Ø¯ÙŠÙ†Ø©"),
            "المدينة",
        )

    def test_health_loads_initial_snapshot_once(self):
        jobicy_job = self.server.normalize_job(
            {
                "jobTitle": "Backend Engineer",
                "companyName": "Example",
                "jobGeo": "Worldwide",
                "url": "https://jobicy.com/jobs/backend-engineer",
                "pubDate": "2026-06-01T12:00:00Z",
            },
            "jobicy",
        )
        with patch.dict(
            self.server.SOURCE_FETCHERS,
            {"jobicy": lambda: [jobicy_job], "himalayas": lambda: []},
        ):
            with self.server.cache_lock:
                self.server.cache["metadata"]["last_refresh_attempt_at"] = None
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["metadata"]["job_count"], 1)

    def test_failed_refresh_keeps_last_successful_snapshot(self):
        job = self.server.normalize_job(
            {
                "jobTitle": "Backend Engineer",
                "companyName": "Example",
                "jobGeo": "Worldwide",
                "url": "https://jobicy.com/jobs/backend-engineer",
                "pubDate": "2026-06-01T12:00:00Z",
            },
            "jobicy",
        )
        with patch.dict(
            self.server.SOURCE_FETCHERS,
            {"jobicy": lambda: [job], "himalayas": lambda: []},
        ):
            self.assertEqual(self.server.refresh_jobs()["status"], "ok")

        def fail():
            raise requests.RequestException("temporary outage")

        with patch.dict(self.server.SOURCE_FETCHERS, {"jobicy": fail, "himalayas": fail}):
            self.assertEqual(self.server.refresh_jobs()["status"], "failed")

        response = self.client.get("/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["metadata"]["total"], 1)

    def test_paid_gateway_blocks_data_but_keeps_health_public(self):
        os.environ["REQUIRE_PAID_GATEWAY"] = "true"
        os.environ["PAID_GATEWAY_SECRETS"] = "rapidapi-secret,other-market-secret"
        os.environ["PAID_GATEWAY_SECRET_HASHES"] = (
            "4e598f5daafc2fda61641ddbb5956deb23fde6616366dc9dd5a7c9f47da4d787"
        )
        with self.server.cache_lock:
            self.server.cache["metadata"]["last_refresh_attempt_at"] = self.server.now_iso()

        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/jobs").status_code, 402)
        self.assertEqual(
            self.client.get("/jobs", headers={"X-API-Gateway-Secret": "other-market-secret"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/jobs", headers={"X-API-Gateway-Secret": "hashed-secret"}).status_code,
            200,
        )

    def test_paid_gateway_fails_closed_by_default(self):
        os.environ.pop("REQUIRE_PAID_GATEWAY", None)
        os.environ.pop("PAID_GATEWAY_SECRETS", None)
        os.environ.pop("PAID_GATEWAY_SECRET_HASHES", None)
        with self.server.cache_lock:
            self.server.cache["metadata"]["last_refresh_attempt_at"] = self.server.now_iso()
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/jobs").status_code, 503)


if __name__ == "__main__":
    unittest.main()
