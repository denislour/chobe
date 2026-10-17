import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("description", models.CharField(blank=True, max_length=1000)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("restricted", models.BooleanField(default=False)),
                ("attributes", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("retired", "Retired")], default="draft", max_length=12)),
                ("version", models.PositiveIntegerField(default=1)),
                ("published", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="categories.category")),
            ],
            options={
                "ordering": ("sort_order", "name", "pk"),
                "permissions": (("publish_category", "Can publish category versions"), ("retire_category", "Can retire categories")),
            },
        ),
        migrations.CreateModel(
            name="CategoryRevision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField()),
                ("snapshot", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="revisions", to="categories.category")),
            ],
            options={
                "ordering": ("-version",),
                "constraints": (models.UniqueConstraint(fields=("category", "version"), name="category_revision_unique"),),
            },
        ),
        migrations.CreateModel(
            name="CategoryAuditEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=20)),
                ("version", models.PositiveIntegerField()),
                ("before", models.JSONField(default=dict)),
                ("after", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="categories.category")),
            ],
            options={"ordering": ("-created_at", "-pk")},
        ),
    ]
