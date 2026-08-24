import argparse
import asyncio
import uuid
from datetime import UTC, datetime

from app.core.database import SessionFactory
from app.models.user import AppReviewInvite, User


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revoke an App Review invitation or grant")
    parser.add_argument("invite_id", type=uuid.UUID)
    return parser.parse_args()


async def run() -> None:
    args = arguments()
    async with SessionFactory() as session, session.begin():
        invite = await session.get(AppReviewInvite, args.invite_id, with_for_update=True)
        if invite is None:
            raise SystemExit("Invitation not found")
        invite.revoked_at = datetime.now(UTC)
        if invite.consumed_by:
            user = await session.get(User, invite.consumed_by, with_for_update=True)
            if user:
                user.review_access_expires_at = datetime.now(UTC)
    print(f"revoked={args.invite_id}")


if __name__ == "__main__":
    asyncio.run(run())
