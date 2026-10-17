

from categories.models import Category


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














