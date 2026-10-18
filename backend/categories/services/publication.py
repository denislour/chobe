from copy import deepcopy

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.services.versioning import (
    save_versioned,
)
from categories.models import Category, CategoryAuditEvent, CategoryRevision
from categories.serializers.attributes import AttributeDefinitionSerializer
from common.exceptions import (
    VersionConflict,
)


def visible_categories():
    published = {
        str(category.pk): category.published
        for category in Category.objects.filter(status=Category.Status.ACTIVE)
        if category.published
    }
    visible = {}
    for key, snapshot in published.items():
        parent = snapshot["parent"]
        seen = {key}
        while parent is not None and parent in published and parent not in seen:
            seen.add(parent)
            parent = published[parent]["parent"]
        if parent is None:
            visible[key] = snapshot
    return visible


def draft_snapshot(category):
    return {
        "id": str(category.pk),
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "parent": str(category.parent_id) if category.parent_id else None,
        "sort_order": category.sort_order,
        "restricted": category.restricted,
        "attributes": deepcopy(category.attributes),
        "version": category.version,
        "status": category.status,
    }


def require_permission(user, permission):
    user = (
        get_user_model()
        .objects.filter(pk=user.pk, is_active=True, is_staff=True)
        .first()
    )
    if user is None or not user.has_perm(f"categories.{permission}"):
        raise PermissionDenied("You do not have permission to change categories.")


def check_parent(category):
    seen = {category.pk}
    parent = category.parent
    depth = 1
    while parent is not None:
        if parent.pk in seen:
            raise ValidationError({"parent": ["A category cannot contain itself."]})
        seen.add(parent.pk)
        depth += 1
        if depth > 4:
            raise ValidationError({"parent": ["Use at most four category levels."]})
        parent = parent.parent
    # Existing descendants must still fit after moving their ancestor.
    frontier = [category.pk]
    while frontier:
        frontier = list(
            Category.objects.filter(parent_id__in=frontier).values_list("pk", flat=True)
        )
        if frontier:
            depth += 1
            if depth > 4:
                raise ValidationError(
                    {"parent": ["This move would make the category tree too deep."]}
                )


def audit(category, user, action, before):
    CategoryAuditEvent.objects.create(
        category=category,
        actor=user,
        action=action,
        version=category.version,
        before=before,
        after=draft_snapshot(category),
    )


def save_draft(user, values, instance=None):
    values = values.copy()
    try:
        with transaction.atomic():
            require_permission(user, "change_category" if instance else "add_category")
            before = {}
            if instance:
                category = Category.objects.select_for_update().get(pk=instance.pk)
                if category.version != values["version"]:
                    raise VersionConflict()
                before = draft_snapshot(category)
                if (
                    category.published
                    and "slug" in values
                    and values["slug"] != category.slug
                ):
                    raise ValidationError(
                        {"slug": ["A published category address cannot change."]}
                    )
                for key, value in values.items():
                    if key != "version":
                        setattr(category, key, value)
                check_parent(category)
                category = save_versioned(category, values)
            else:
                values.pop("version", None)
                category = Category(**values)
                check_parent(category)
                category.save()
            audit(category, user, "updated" if instance else "created", before)
            return category
    except IntegrityError as error:
        raise ValidationError(
            {"slug": ["This category address is already in use."]}
        ) from error


def publish_category(user, instance, version):
    with transaction.atomic():
        require_permission(user, "publish_category")
        category = Category.objects.select_for_update().get(pk=instance.pk)
        if category.version != version:
            raise VersionConflict()
        if category.restricted:
            raise ValidationError(
                {"restricted": ["Restricted categories cannot be published."]}
            )
        check_parent(category)
        fields = AttributeDefinitionSerializer(
            data=category.attributes, many=True, max_length=30
        )
        fields.is_valid(raise_exception=True)
        category.attributes = fields.validated_data
        visible = visible_categories()
        parent_id = str(category.parent_id) if category.parent_id else None
        if parent_id and parent_id not in visible:
            raise ValidationError({"parent": ["Publish the parent category first."]})
        # Published descendants can differ from the draft tree.
        published_parents = {key: item["parent"] for key, item in visible.items()}
        published_parents[str(category.pk)] = parent_id
        for key in published_parents:
            ancestor, branch = key, set()
            while ancestor is not None:
                if ancestor in branch or len(branch) >= 4:
                    raise ValidationError(
                        {"parent": ["This publication would create an invalid tree."]}
                    )
                branch.add(ancestor)
                ancestor = published_parents.get(ancestor)
        before = draft_snapshot(category)
        snapshot = draft_snapshot(category)
        snapshot.pop("restricted")
        snapshot.pop("status")
        snapshot["version"] = version + 1
        category = save_versioned(
            category,
            {
                "version": version,
                "published": snapshot,
                "attributes": category.attributes,
                "status": Category.Status.ACTIVE,
            },
        )
        CategoryRevision.objects.create(
            category=category, version=category.version, snapshot=snapshot, actor=user
        )
        audit(category, user, "published", before)
        return category


def retire_category(user, instance, version):
    with transaction.atomic():
        require_permission(user, "retire_category")
        category = Category.objects.select_for_update().get(pk=instance.pk)
        if category.version != version:
            raise VersionConflict()
        if category.status != Category.Status.ACTIVE:
            raise ValidationError("Only active categories can be retired.")
        if any(
            item["parent"] == str(category.pk) for item in visible_categories().values()
        ):
            raise ValidationError(
                "Retire or move the published child categories first."
            )
        before = draft_snapshot(category)
        category = save_versioned(
            category, {"version": version, "status": Category.Status.RETIRED}
        )
        audit(category, user, "retired", before)
        return category
