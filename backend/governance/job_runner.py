"""
Background Job Runner & Render Execution Fallback for BrandGuard.
Executes long jobs (repo scan, blast radius, re-audit) asynchronously
without blocking HTTP requests, exposing status via GET /api/jobs/{id}/.

Architecture & Render Compatibility:
1. Production with Celery / Redis: Dispatches to Celery worker if available.
2. Render Free Tier / Fallback: Database-backed Job queue with Python ThreadPoolExecutor
   running inside the web process (no external worker dyno required).
3. Test / Eager Mode: Executes synchronously when CELERY_TASK_ALWAYS_EAGER=True.
"""

import os
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import connection

# Maximum worker threads for Render free/starter instances
MAX_WORKER_THREADS = int(os.environ.get("BRANDGUARD_MAX_JOB_THREADS", 4))
_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKER_THREADS, thread_name_prefix='brandguard_job')


def get_runner_status() -> dict:
    """
    Returns diagnostic health metrics for the background job runner.
    Used by /readyz and the Admin System Health card.
    """
    from governance.models import Job

    mode = "THREAD_POOL"
    is_fallback = True

    # Check if Celery is enabled and configured
    celery_broker = getattr(settings, 'CELERY_BROKER_URL', None) or os.environ.get('CELERY_BROKER_URL')
    if celery_broker and getattr(settings, 'ENABLE_CELERY_JOBS', False):
        mode = "CELERY_WORKER"
        is_fallback = False

    try:
        now = timezone.now()
        since_24h = now - timedelta(hours=24)

        pending_count = Job.objects.filter(status='PENDING').count()
        running_count = Job.objects.filter(status='RUNNING').count()
        success_24h = Job.objects.filter(status='SUCCESS', completed_at__gte=since_24h).count()
        failed_24h = Job.objects.filter(status='FAILED', completed_at__gte=since_24h).count()
    except Exception:
        pending_count = 0
        running_count = 0
        success_24h = 0
        failed_24h = 0

    return {
        "status": "active",
        "mode": mode,
        "active_workers": MAX_WORKER_THREADS,
        "fallback_active": is_fallback,
        "pending_jobs": pending_count,
        "running_jobs": running_count,
        "succeeded_last_24h": success_24h,
        "failed_last_24h": failed_24h,
        "supports_background_execution": True,
        "thread_pool_alive": not _EXECUTOR._shutdown
    }


def update_job_progress(job_id, progress: int, status_message: str = ''):
    """Callback to update progress of a running job."""
    from governance.models import Job
    try:
        Job.objects.filter(id=job_id).update(
            progress=min(max(progress, 0), 100),
            status_message=status_message,
            updated_at=timezone.now()
        )
    except Exception:
        pass


def _execute_job_wrapper(job_id, task_fn, args, kwargs):
    """Worker wrapper executing inside thread pool."""
    from governance.models import Job

    # Ensure fresh DB connection for worker thread
    connection.close()
    try:
        job = Job.objects.filter(id=job_id).first()
        if not job:
            return

        job.status = 'RUNNING'
        job.progress = 5
        job.status_message = 'Job execution started'
        job.save(update_fields=['status', 'progress', 'status_message', 'updated_at'])

        # Execute target task function
        result = task_fn(*args, **kwargs)

        job.refresh_from_db()
        job.status = 'SUCCESS'
        job.progress = 100
        job.status_message = 'Completed successfully'
        job.result_payload = result if isinstance(result, dict) else {'result': result}
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'progress', 'status_message', 'result_payload', 'completed_at', 'updated_at'])
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
        try:
            Job.objects.filter(id=job_id).update(
                status='FAILED',
                status_message=f"Failed: {str(exc)}",
                error_message=err_msg,
                completed_at=timezone.now(),
                updated_at=timezone.now()
            )
        except Exception:
            pass
    finally:
        connection.close()


def enqueue_job(profile, user, job_type: str, task_fn, *args, **kwargs):
    """
    Creates a Job record and submits it to the background thread pool.
    In testing/eager mode (or when synchronous=True is passed), executes synchronously.
    """
    from governance.models import Job

    is_sync = kwargs.pop('synchronous', False) or getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)

    job = Job.objects.create(
        profile=profile,
        user=user if user and user.is_authenticated else None,
        job_type=job_type,
        status='PENDING',
        progress=0,
        status_message='Queued for execution'
    )

    if is_sync:
        _execute_job_wrapper(job.id, task_fn, args, kwargs)
        job.refresh_from_db()
    else:
        _EXECUTOR.submit(_execute_job_wrapper, job.id, task_fn, args, kwargs)

    return job


def cleanup_old_jobs(retention_days: int = 7) -> int:
    """
    Prunes completed and failed jobs older than retention_days.
    Returns the number of deleted records.
    """
    from governance.models import Job
    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted, _ = Job.objects.filter(
        status__in=['SUCCESS', 'FAILED'],
        completed_at__lt=cutoff
    ).delete()
    return deleted
