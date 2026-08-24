import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing, ListingStatus
from app.models.marketplace_event import ListingEvent
from app.models.messaging import Conversation, ConversationMember, Message
from app.models.pickup import PickupSession, PickupStatus
from app.models.report import (
    AdminAction,
    Report,
    ReportReason,
    ReportSeverity,
    ReportStatus,
    ReportTarget,
)
from app.models.reservation import (
    Reservation,
    ReservationStatus,
    WaitlistEntry,
    WaitlistStatus,
)
from app.models.user import User
from app.schemas.report import AdminResolutionAction
from app.services.listing_lifecycle import transition_listing


class ReportError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def severity_for(reason: ReportReason) -> ReportSeverity:
    if reason in {ReportReason.PROHIBITED_ITEM, ReportReason.HARASSMENT}:
        return ReportSeverity.HIGH
    if reason in {ReportReason.SCAM_FRAUD, ReportReason.COUNTERFEIT_STOLEN}:
        return ReportSeverity.MEDIUM
    return ReportSeverity.LOW


async def validate_target(
    session: AsyncSession,
    reporter_id: uuid.UUID,
    target_type: ReportTarget,
    target_id: uuid.UUID,
) -> tuple[dict[str, uuid.UUID | None], uuid.UUID | None]:
    columns: dict[str, uuid.UUID | None] = {
        "listing_id": None,
        "reported_user_id": None,
        "message_id": None,
    }
    event_listing_id: uuid.UUID | None = None
    if target_type == ReportTarget.LISTING:
        listing = await session.get(Listing, target_id)
        if listing is None or listing.seller_id == reporter_id:
            raise ReportError("report_target_not_found", "This content is unavailable.")
        columns["listing_id"] = listing.id
        event_listing_id = listing.id
    elif target_type == ReportTarget.USER:
        target = await session.get(User, target_id)
        if target is None or target.id == reporter_id:
            raise ReportError("report_target_not_found", "This user is unavailable.")
        columns["reported_user_id"] = target.id
    else:
        message = await session.get(Message, target_id)
        if message is None or message.sender_id in {None, reporter_id}:
            raise ReportError("report_target_not_found", "This message is unavailable.")
        member = await session.get(ConversationMember, (message.conversation_id, reporter_id))
        if member is None:
            raise ReportError("report_target_not_found", "This message is unavailable.")
        conversation = await session.get(Conversation, message.conversation_id)
        columns["message_id"] = message.id
        event_listing_id = conversation.listing_id if conversation else None
    return columns, event_listing_id


async def create_report(
    session: AsyncSession,
    reporter_id: uuid.UUID,
    target_type: ReportTarget,
    target_id: uuid.UUID,
    reason: ReportReason,
    details: str | None,
) -> Report:
    async with session.begin():
        columns, event_listing_id = await validate_target(
            session, reporter_id, target_type, target_id
        )
        target_column = {
            ReportTarget.LISTING: Report.listing_id,
            ReportTarget.USER: Report.reported_user_id,
            ReportTarget.MESSAGE: Report.message_id,
        }[target_type]
        existing = await session.scalar(
            select(Report).where(
                Report.reporter_id == reporter_id,
                Report.target_type == target_type,
                target_column == target_id,
                Report.reason == reason,
                Report.status.in_([ReportStatus.OPEN, ReportStatus.IN_REVIEW]),
            )
        )
        if existing:
            return existing
        report = Report(
            id=uuid.uuid4(),
            reporter_id=reporter_id,
            target_type=target_type,
            reason=reason,
            severity=severity_for(reason),
            details=details.strip() if details else None,
            status=ReportStatus.OPEN,
            **columns,
        )
        session.add(report)
        if event_listing_id:
            session.add(
                ListingEvent(
                    listing_id=event_listing_id,
                    actor_id=reporter_id,
                    event_type="UserReported",
                    event_data={
                        "report_id": str(report.id),
                        "target_type": target_type.value,
                        "reason": reason.value,
                    },
                )
            )
    return report


async def reported_user_id(session: AsyncSession, report: Report) -> uuid.UUID:
    if report.reported_user_id:
        return report.reported_user_id
    if report.listing_id:
        listing = await session.get(Listing, report.listing_id)
        if listing:
            return listing.seller_id
    if report.message_id:
        message = await session.get(Message, report.message_id)
        if message and message.sender_id:
            return message.sender_id
    raise ReportError("report_target_not_found", "The reported user is unavailable.")


async def remove_reported_listing(
    session: AsyncSession, report: Report, admin_id: uuid.UUID
) -> uuid.UUID:
    if report.listing_id is None:
        raise ReportError("action_target_mismatch", "This report does not target a listing.")
    listing = await session.scalar(
        select(Listing).where(Listing.id == report.listing_id).with_for_update(of=Listing)
    )
    if listing is None:
        raise ReportError("report_target_not_found", "The listing is unavailable.")
    if listing.status == ListingStatus.REMOVED:
        return listing.id
    if listing.status not in {ListingStatus.ACTIVE, ListingStatus.RESERVED}:
        raise ReportError("listing_not_removable", "This listing is not publicly available.")
    reservations = await session.scalars(
        select(Reservation)
        .where(
            Reservation.listing_id == listing.id,
            Reservation.status == ReservationStatus.ACTIVE,
        )
        .with_for_update()
    )
    for reservation in reservations:
        reservation.status = ReservationStatus.CANCELLED
        pickup = await session.scalar(
            select(PickupSession)
            .where(PickupSession.reservation_id == reservation.id)
            .with_for_update()
        )
        if pickup and pickup.status in {PickupStatus.PROPOSED, PickupStatus.SCHEDULED}:
            pickup.status = PickupStatus.CANCELLED
            pickup.cancelled_at = datetime.now(UTC)
    waitlist = await session.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.listing_id == listing.id,
            WaitlistEntry.status.in_([WaitlistStatus.WAITING, WaitlistStatus.OFFERED]),
        )
        .with_for_update()
    )
    for entry in waitlist:
        entry.status = WaitlistStatus.REMOVED
    session.add(
        transition_listing(
            listing,
            ListingStatus.REMOVED,
            admin_id,
            "ListingRemoved",
            {"report_id": str(report.id)},
        )
    )
    return listing.id


async def resolve_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    admin_id: uuid.UUID,
    action: AdminResolutionAction,
    notes: str | None,
) -> Report:
    async with session.begin():
        report = await session.scalar(
            select(Report).where(Report.id == report_id).with_for_update()
        )
        if report is None:
            raise ReportError("report_not_found", "This report is unavailable.")
        if report.reporter_id == admin_id:
            raise ReportError("self_review_forbidden", "Another moderator must review this report.")
        if report.status not in {ReportStatus.OPEN, ReportStatus.IN_REVIEW}:
            raise ReportError("report_already_resolved", "This report is already resolved.")
        target_id = report.target_id
        if action == AdminResolutionAction.REMOVE_LISTING:
            target_id = await remove_reported_listing(session, report, admin_id)
        elif action == AdminResolutionAction.SUSPEND_USER:
            target_id = await reported_user_id(session, report)
            if target_id == admin_id:
                raise ReportError("self_action_forbidden", "A moderator cannot suspend themselves.")
            target = await session.scalar(
                select(User).where(User.id == target_id).with_for_update()
            )
            if target is None:
                raise ReportError("report_target_not_found", "The user is unavailable.")
            target.suspended_at = datetime.now(UTC)
        report.status = (
            ReportStatus.DISMISSED
            if action == AdminResolutionAction.DISMISS
            else ReportStatus.RESOLVED
        )
        report.assigned_admin_id = admin_id
        report.resolution = action.value
        report.resolved_at = datetime.now(UTC)
        session.add(
            AdminAction(
                admin_id=admin_id,
                report_id=report.id,
                action_type=action.value,
                target_type=report.target_type.value,
                target_id=target_id,
                notes=notes.strip() if notes else None,
            )
        )
    return report
