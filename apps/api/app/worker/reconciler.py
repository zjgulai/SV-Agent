import argparse
import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.outbox import (
    publish_job_outbox,
    reconcile_pending_outbox,
    retry_dead_outbox,
)
from app.settings import settings
from app.worker.tasks import dispatch_job

LOGGER = logging.getLogger(__name__)
RECONCILE_INTERVAL_SECONDS = 5


async def run_once() -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        result = await reconcile_pending_outbox(factory, dispatch_job)
        if result.claimed or result.dead_lettered:
            LOGGER.info(
                "reconciled outbox claimed=%s published=%s failed=%s dead_lettered=%s",
                result.claimed,
                result.published,
                result.failed,
                result.dead_lettered,
            )
    finally:
        await engine.dispose()


async def run_forever() -> None:
    while True:
        try:
            await run_once()
        except Exception:
            LOGGER.exception("outbox reconciliation pass failed")
        await asyncio.sleep(RECONCILE_INTERVAL_SECONDS)


async def retry_dead_letter(job_id: UUID) -> None:
    """Run only through a deployment operator channel; no HTTP endpoint exists."""

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            job = await retry_dead_outbox(session, job_id=job_id)
        async with factory() as session:
            result = await publish_job_outbox(session, dispatch_job, job_id=job.id)
        LOGGER.info(
            "manual dead-letter retry scheduled job_id=%s claimed=%s published=%s failed=%s",
            job.id,
            result.claimed,
            result.published,
            result.failed,
        )
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Outbox reconciler operator commands")
    commands = parser.add_subparsers(dest="command")
    retry = commands.add_parser("retry-dead-letter")
    retry.add_argument("--job-id", type=UUID, required=True)
    retry.add_argument("--confirm", choices=["DEAD_LETTER_RETRY"], required=True)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    if args.command == "retry-dead-letter":
        asyncio.run(retry_dead_letter(args.job_id))
    else:
        asyncio.run(run_forever())
