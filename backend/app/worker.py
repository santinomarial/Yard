import asyncio

import structlog

from app.core.database import SessionFactory
from app.services.notifications import (
    deliver_pending_notifications,
    enqueue_due_notifications,
    notification_provider,
)
from app.services.reservations import expire_due_reservations

logger = structlog.get_logger()


async def run_once() -> None:
    async with SessionFactory() as session:
        expired = await expire_due_reservations(session)
    async with SessionFactory() as session:
        queued = await enqueue_due_notifications(session)
    async with SessionFactory() as session:
        sent, failed = await deliver_pending_notifications(session, notification_provider())
    logger.info(
        "worker_cycle",
        reservations_expired=expired,
        notifications_queued=queued,
        notifications_sent=sent,
        notifications_failed=failed,
    )


async def main() -> None:
    logger.info("worker_started")
    while True:
        try:
            await run_once()
        except Exception:
            logger.exception("worker_cycle_failed")
        await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
