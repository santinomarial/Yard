import argparse
import asyncio

from app.core.database import SessionFactory
from app.services.review_access import create_review_invite


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create one single-use App Review invitation")
    parser.add_argument("--purpose", required=True, help="Release/build or review ticket")
    parser.add_argument(
        "--created-by", required=True, help="Operator identifier for the audit record"
    )
    parser.add_argument("--hours", type=int, default=48, choices=range(1, 73))
    return parser.parse_args()


async def run() -> None:
    args = arguments()
    async with SessionFactory() as session:
        invite, code = await create_review_invite(
            session,
            purpose=args.purpose,
            created_by=args.created_by,
            lifetime_hours=args.hours,
        )
    print(f"invite_id={invite.id}")
    print(f"code={code}")
    print(f"expires_at={invite.expires_at.isoformat()}")
    print("Store this code only in private App Review notes; it cannot be recovered later.")


if __name__ == "__main__":
    asyncio.run(run())
