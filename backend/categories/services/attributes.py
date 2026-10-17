import math

from django.http import Http404
from rest_framework.exceptions import ValidationError

from accounts.services.versioning import VersionConflict
from categories.services.publication import visible_categories


def validate_category_attributes(category_id, schema_version, values):
    snapshot = visible_categories().get(str(category_id))
    if snapshot is None:
        raise Http404
    if snapshot["version"] != schema_version:
        raise VersionConflict(
            "The category schema has changed. Reload the fields and review your values."
        )
    definitions = {field["key"]: field for field in snapshot["attributes"]}
    errors = {
        key: ["This field does not belong to this category."]
        for key in values
        if key not in definitions
    }
    cleaned = {}
    for key, field in definitions.items():
        value = values.get(key)
        if value is None or value == "":
            if field["required"]:
                errors[key] = ["This field is required."]
            continue
        kind = field["type"]
        valid = False
        if kind == "text":
            valid = isinstance(value, str) and len(value.strip()) <= field["max_length"]
            value = value.strip() if isinstance(value, str) else value
            valid = valid and (bool(value) or not field["required"])
        elif kind in ("integer", "number"):
            valid = (
                type(value) is int if kind == "integer" else type(value) in (int, float)
            )
            valid = valid and abs(value) <= 10**15 and math.isfinite(value)
            if valid:
                minimum, maximum = field["min_value"], field["max_value"]
                valid = (minimum is None or value >= minimum) and (
                    maximum is None or value <= maximum
                )
        elif kind == "boolean":
            valid = type(value) is bool
        elif kind == "select":
            valid = isinstance(value, str) and value in {
                item["value"] for item in field["choices"]
            }
        if valid:
            cleaned[key] = value
        else:
            errors[key] = [f"Enter a valid {kind} value for {field['label']}."]
    if errors:
        raise ValidationError({"attributes": errors})
    return cleaned
