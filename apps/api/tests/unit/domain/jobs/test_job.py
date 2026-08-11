import pytest

from app.domain.jobs.entities import Job, JobState, JobType
from app.domain.jobs.errors import InvalidJobTransition


def test_terminal_job_cannot_return_to_running() -> None:
    job = Job.new(JobType.SCRIPT_GENERATION, "key-1", "a" * 64)
    job = job.transition_to(JobState.GENERATING)
    job = job.transition_to(JobState.VALIDATING)
    job = job.transition_to(JobState.SUCCEEDED)

    with pytest.raises(InvalidJobTransition):
        job.transition_to(JobState.GENERATING)


def test_product_import_cannot_enter_script_generation_state() -> None:
    job = Job.new(JobType.PRODUCT_IMPORT, "key-1", "a" * 64)

    with pytest.raises(InvalidJobTransition):
        job.transition_to(JobState.GENERATING)
