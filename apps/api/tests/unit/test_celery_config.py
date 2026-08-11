from uuid import uuid4

import pytest
from celery.exceptions import Retry  # type: ignore[import-untyped]
from sqlalchemy.exc import SQLAlchemyError

from app.worker import tasks
from app.worker.celery_app import celery_app
from app.worker.tasks import _is_retry_or_redelivery, generate_script, import_product


def test_worker_requeues_tasks_lost_with_a_worker() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_acks_on_failure_or_timeout is False
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_tasks_retry_transient_infrastructure_failures() -> None:
    assert SQLAlchemyError in generate_script.autoretry_for
    assert OSError in generate_script.autoretry_for
    assert SQLAlchemyError in import_product.autoretry_for
    assert generate_script.retry_backoff is True
    assert generate_script.max_retries is None


def test_celery_retry_is_treated_as_fenced_redelivery() -> None:
    class Request:
        def __init__(self) -> None:
            self.retries = 1
            self.delivery_info: dict[str, object] = {}

    class Task:
        def __init__(self) -> None:
            self.request = Request()

    assert _is_retry_or_redelivery(Task()) is True


def test_database_failure_before_worker_start_is_autoretried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = SQLAlchemyError("database unavailable before job start")

    async def fail_before_start(_job_id: object, *, allow_retry: bool = False) -> None:
        del allow_retry
        raise failure

    retried: list[BaseException] = []

    def retry(*, exc: BaseException, **_kwargs: object) -> None:
        retried.append(exc)
        raise Retry()

    monkeypatch.setattr(tasks, "_run_generation", fail_before_start)
    monkeypatch.setattr(generate_script, "retry", retry)

    with pytest.raises(Retry):
        generate_script.run(str(uuid4()))

    assert retried == [failure]
