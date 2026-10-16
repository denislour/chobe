import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Shop",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("description", models.CharField(max_length=1000)),
                ("area", models.CharField(max_length=120)),
                ("contact_hours", models.CharField(blank=True, max_length=120)),
                ("website_url", models.URLField(blank=True, max_length=400)),
                ("social_url", models.URLField(blank=True, max_length=400)),
                ("logo", models.BinaryField(blank=True, default=bytes)),
                ("banner", models.BinaryField(blank=True, default=bytes)),
                ("status", models.CharField(choices=[("active", "Active"), ("paused", "Paused"), ("suspended", "Suspended"), ("closed", "Closed")], default="active", max_length=12)),
                ("suspended_from", models.CharField(blank=True, max_length=12)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="shop", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ShopSlug",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slugs", to="shops.shop")),
            ],
        ),
        migrations.CreateModel(
            name="ShopAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=24)),
                ("changes", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="shops.shop")),
            ],
            options={"ordering": ("-created_at", "-pk")},
        ),
    ]
