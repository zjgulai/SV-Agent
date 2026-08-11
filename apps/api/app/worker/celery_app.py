from celery import Celery  # type: ignore[import-untyped]

from app.settings import settings

celery_app = Celery(
    "reverse_engineer_mode",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_acks_late=True,
    task_acks_on_failure_or_timeout=False,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    timezone="UTC",
)
