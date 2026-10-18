import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("listings", "0002_search_index"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                        name='ModerationCase',
                        fields=[
                            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                            ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=12)),
                            ('source', models.CharField(default='manual', max_length=12)),
                            ('reason', models.CharField(blank=True, max_length=2000)),
                            ('appeal', models.CharField(blank=True, max_length=2000)),
                            ('appeal_open', models.BooleanField(default=False)),
                            ('version', models.PositiveIntegerField(default=1)),
                            ('created_at', models.DateTimeField(auto_now_add=True)),
                            ('updated_at', models.DateTimeField(auto_now=True)),
                            ('revision', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='moderation', to='listings.listingrevision')),
                        ],
                        options={
                            "db_table": "listings_moderationcase",
                            'ordering': ('-created_at', '-pk'),
                        },
                    ),
                migrations.CreateModel(
                        name='Report',
                        fields=[
                            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                            ('reason', models.CharField(choices=[('prohibited', 'Prohibited'), ('fraud', 'Fraud'), ('incorrect', 'Incorrect'), ('images', 'Images'), ('spam', 'Spam'), ('other', 'Other')], max_length=12)),
                            ('description', models.CharField(max_length=2000)),
                            ('status', models.CharField(choices=[('open', 'Open'), ('reviewing', 'Reviewing'), ('resolved', 'Resolved'), ('dismissed', 'Dismissed')], default='open', max_length=12)),
                            ('response', models.CharField(blank=True, max_length=500)),
                            ('version', models.PositiveIntegerField(default=1)),
                            ('created_at', models.DateTimeField(auto_now_add=True)),
                            ('listing', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='listings.listing')),
                            ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                            ('shop', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shops.shop')),
                        ],
                        options={
                            "db_table": "listings_report",
                            'ordering': ('-created_at', '-pk'),
                            'permissions': [('review_report', 'Can review marketplace reports')],
                        },
                    ),
                migrations.CreateModel(
                        name='ReportDecision',
                        fields=[
                            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                            ('action', models.CharField(max_length=16)),
                            ('reason', models.CharField(max_length=2000)),
                            ('created_at', models.DateTimeField(auto_now_add=True)),
                            ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                            ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='decisions', to='moderation.report')),
                        ],
                        options={"db_table": "listings_reportdecision"},
                    ),
                migrations.AddConstraint(
                        model_name='report',
                        constraint=models.CheckConstraint(condition=models.Q(models.Q(('listing__isnull', False), ('shop__isnull', True)), models.Q(('listing__isnull', True), ('shop__isnull', False)), _connector='OR'), name='report_one_target'),
                    ),
            ],
        ),
    ]
