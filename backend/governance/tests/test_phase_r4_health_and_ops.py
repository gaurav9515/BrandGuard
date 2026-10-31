"""
Phase R4 Production Operations, Health Probes & Job Runner Fallback Test Suite.
Verifies:
1. /healthz returns 200 with database status and latency
2. /readyz returns 200 with database, migrations, job_runner, and storage checks
3. 503 response on simulated database failure
4. Background job runner status reporting and database-backed thread pool fallback
5. Cleanup of old completed/failed background jobs
"""

import json
from unittest.mock import patch
from datetime import timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.db import DatabaseError
from governance.models import Job, BrandProfile, Organization, Company
from governance.job_runner import get_runner_status, enqueue_job, cleanup_old_jobs


class PhaseR4HealthAndOpsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.org, _ = Organization.objects.get_or_create(name="Health Org", slug="health-org")
        self.company, _ = Company.objects.get_or_create(organization=self.org, name="Health Brand", slug="health-brand")
        self.profile, _ = BrandProfile.objects.get_or_create(
            company=self.company,
            defaults={"org_name": "Health Brand", "allowed_hex_palette": []}
        )

    def test_01_healthz_endpoint_healthy(self):
        """GET /healthz returns 200 OK with connected database latency."""
        res = self.client.get('/healthz')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("database", data)
        self.assertEqual(data["database"].get("status"), "connected")
        self.assertGreaterEqual(data["database"].get("latency_ms", 0), 0)

    def test_02_readyz_endpoint_ready(self):
        """GET /readyz returns 200 OK with detailed subsystem status."""
        res = self.client.get('/readyz')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ready")
        checks = data.get("checks", {})
        self.assertIn("database", checks)
        self.assertEqual(checks["database"].get("status"), "connected")
        self.assertIn("migrations", checks)
        self.assertEqual(checks["migrations"].get("status"), "up_to_date")
        self.assertIn("job_runner", checks)
        self.assertEqual(checks["job_runner"].get("status"), "active")
        self.assertIn("storage", checks)
        self.assertEqual(checks["storage"].get("status"), "writable")

    def test_03_healthz_unhealthy_on_db_failure(self):
        """GET /healthz returns 503 Service Unavailable when DB is down."""
        with patch("django.db.connection.cursor", side_effect=DatabaseError("Connection lost")):
            res = self.client.get('/healthz')
            self.assertEqual(res.status_code, 503)
            data = res.json()
            self.assertEqual(data.get("status"), "unhealthy")
            self.assertEqual(data["database"].get("status"), "unreachable")

    def test_04_readyz_not_ready_on_db_failure(self):
        """GET /readyz returns 503 when database check fails."""
        with patch("django.db.connection.cursor", side_effect=DatabaseError("Connection lost")):
            res = self.client.get('/readyz')
            self.assertEqual(res.status_code, 503)
            data = res.json()
            self.assertEqual(data.get("status"), "not_ready")
            self.assertEqual(data["checks"]["database"].get("status"), "failed")

    def test_05_job_runner_fallback_status(self):
        """get_runner_status reports active thread pool fallback when Celery is not configured."""
        status = get_runner_status()
        self.assertEqual(status.get("status"), "active")
        self.assertIn(status.get("mode"), ("THREAD_POOL", "CELERY_WORKER"))
        self.assertTrue(status.get("supports_background_execution"))

    def test_06_job_execution_and_cleanup(self):
        """enqueue_job executes tasks and cleanup_old_jobs prunes stale jobs."""
        def sample_task(x, y):
            return {"sum": x + y}

        # Synchronous test execution
        job = enqueue_job(self.profile, None, "TEST_SUM", sample_task, 10, 20, synchronous=True)
        self.assertEqual(job.status, "SUCCESS")
        self.assertEqual(job.result_payload.get("sum"), 30)

        # Backdate completed_at to 10 days ago
        Job.objects.filter(id=job.id).update(
            completed_at=timezone.now() - timedelta(days=10)
        )

        deleted = cleanup_old_jobs(retention_days=7)
        self.assertGreaterEqual(deleted, 1)
        self.assertFalse(Job.objects.filter(id=job.id).exists())

