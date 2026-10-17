from copy import deepcopy
from datetime import timedelta

from django.utils import timezone

from listings.models import ListingAuditEvent, ListingRevision, ModerationCase
from listings.services.management import draft_snapshot, erase_listing, six_months_after


def story_event(listing, actor, action, when, reason=""):
    event = ListingAuditEvent.objects.create(
        listing=listing,
        actor=actor,
        action=action,
        version=listing.version,
        reason=reason,
        source="manual",
    )
    ListingAuditEvent.objects.filter(pk=event.pk).update(created_at=when)


def submitted_revision(listing, when):
    listing.submitted_version = listing.version
    snapshot = draft_snapshot(listing)
    snapshot["category_schema"] = deepcopy(listing.category.published)
    revision = ListingRevision.objects.create(
        listing=listing, version=listing.version, snapshot=snapshot
    )
    ListingRevision.objects.filter(pk=revision.pk).update(created_at=when)
    case = ModerationCase.objects.create(revision=revision)
    ModerationCase.objects.filter(pk=case.pk).update(created_at=when, updated_at=when)
    story_event(listing, listing.shop.owner, "submitted", when)
    return revision, case


def seed_listing_story(listing, story, users, created_at):
    owner = listing.shop.owner
    moderator = users["demo_moderator"]
    now = timezone.now()
    if story in ("due_soon", "expired", "retention_deleted"):
        created_at = now - timedelta(days=190 if story == "due_soon" else 215)
        ListingRevision.objects.filter(listing=listing).delete()
        type(listing).objects.filter(pk=listing.pk).update(created_at=created_at)
        listing.last_owner_action_at = now - timedelta(
            days=175 if story == "due_soon" else 200
        )
        listing.retention_due_at = six_months_after(listing.last_owner_action_at)
    story_event(listing, owner, "draft_saved", created_at)
    if story == "draft":
        listing.description = ""
        listing.rights_confirmed = False
        listing.save()
        return
    for index, image in enumerate(listing.images.all()):
        listing.version += 1
        story_event(
            listing, owner, "image_added", created_at + timedelta(minutes=15 + index)
        )
    listing.version += 1
    revision, case = submitted_revision(listing, created_at + timedelta(hours=1))
    listing.status = "pending"
    if story == "pending":
        listing.save()
        return
    rejected = story == "rejected"
    listing.version += 1
    case.status = "rejected" if rejected else "approved"
    case.reason = (
        "Demo manual review: add clearer wear photos and explain the item condition."
        if rejected
        else "Demo manual review: the submitted details and photo rights confirmation are acceptable."
    )
    case.version += 1
    case.save()
    ModerationCase.objects.filter(pk=case.pk).update(
        updated_at=created_at + timedelta(hours=2)
    )
    story_event(
        listing,
        moderator,
        "reject" if rejected else "approve",
        created_at + timedelta(hours=2),
        case.reason,
    )
    listing.status = "rejected" if rejected else "active"
    if not rejected:
        listing.published = deepcopy(revision.snapshot)
        listing.published_at = created_at + timedelta(hours=2)
    if rejected and owner.username in ("demo_minh", "demo_thao", "demo_linh"):
        case.appeal = "Demo appeal: I can provide clearer details. Please review the condition notes again."
        case.appeal_open = True
        case.version += 1
        case.save()
        story_event(
            listing, owner, "appealed", created_at + timedelta(hours=3), case.appeal
        )
    if story in ("hidden", "sold", "report_hold"):
        listing.status = "sold" if story == "sold" else "hidden"
        listing.moderation_hold = story == "report_hold"
        listing.submitted_version = None
        listing.version += 1
        story_event(
            listing,
            moderator if story == "report_hold" else owner,
            "report_hidden" if story == "report_hold" else f"status_{listing.status}",
            created_at + timedelta(hours=3),
            "Demo report action: temporarily hidden pending clarification."
            if story == "report_hold"
            else "",
        )
    if story in ("pending_edit", "rejected_edit", "draft_edit"):
        listing.version += 1
        listing.title += " — revised draft"
        listing.description += (
            " Unpublished update: the owner is clarifying a small condition detail."
        )
        listing.submitted_version = None
        story_event(listing, owner, "draft_saved", created_at + timedelta(days=1))
        if story != "draft_edit":
            listing.version += 1
            _, edited_case = submitted_revision(
                listing, created_at + timedelta(days=1, hours=1)
            )
            listing.status = "pending"
            if story == "rejected_edit":
                listing.version += 1
                listing.status = "rejected"
                edited_case.status = "rejected"
                edited_case.reason = "Demo manual review: clarify the revised condition statement. The previous approved version remains public."
                edited_case.version += 1
                edited_case.save()
                story_event(
                    listing,
                    moderator,
                    "reject",
                    created_at + timedelta(days=1, hours=2),
                    edited_case.reason,
                )
    if story == "reapproved":
        listing.published = {}
        listing.status = "rejected"
        listing.version += 1
        case.status = "rejected"
        case.reason = "Demo re-review: initial condition notes needed clarification."
        case.version += 1
        case.save()
        story_event(
            listing, moderator, "reject", created_at + timedelta(hours=3), case.reason
        )
        case.appeal = "Demo appeal: the original notes include the requested details."
        case.appeal_open = True
        case.version += 1
        case.save()
        story_event(
            listing, owner, "appealed", created_at + timedelta(hours=4), case.appeal
        )
        case.status = "approved"
        case.reason = "Demo appeal reviewed manually; this exact submitted snapshot is approved again."
        case.appeal_open = False
        case.version += 1
        case.save()
        listing.version += 1
        listing.status = "active"
        listing.published = deepcopy(revision.snapshot)
        listing.published_at = created_at + timedelta(hours=5)
        story_event(
            listing, moderator, "approve", created_at + timedelta(hours=5), case.reason
        )
    if story == "phone_withdrawn":
        listing.published["phone_consent"] = True
        listing.phone_consent = False
        listing.version += 1
        story_event(
            listing,
            owner,
            "draft_saved",
            created_at + timedelta(hours=3),
            "Demo: per-listing phone consent withdrawn.",
        )
    listing.save()
    if story in ("owner_deleted", "retention_deleted"):
        erase_listing(
            listing,
            owner if story == "owner_deleted" else None,
            "owner_deleted" if story == "owner_deleted" else "retention_deleted",
        )
