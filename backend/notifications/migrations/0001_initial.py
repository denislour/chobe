import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("listings", "0002_search_index"),
        ("engagement", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                        name='NotificationPreference',
                        fields=[
                            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                            ('inbox', models.BooleanField(default=False)),
                            ('email', models.BooleanField(default=False)),
                            ('version', models.PositiveIntegerField(default=1)),
                            ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                        ],
                        options={"db_table": "listings_notificationpreference"},
                    ),
                migrations.CreateModel(
                        name='Notification',
                        fields=[
                            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                            ('listing_version', models.PositiveIntegerField()),
                            ('read_at', models.DateTimeField(blank=True, null=True)),
                            ('email_status', models.CharField(default='blocked', max_length=12)),
                            ('created_at', models.DateTimeField(auto_now_add=True)),
                            ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='listings.listing')),
                            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                            ('search', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='engagement.savedsearch')),
                        ],
                        options={
                            "db_table": "listings_notification",
                            'ordering': ('-created_at', '-pk'),
                        },
                    ),
                migrations.AddConstraint(
                        model_name='notification',
                        constraint=models.UniqueConstraint(fields=('search', 'listing', 'listing_version'), name='listing_notification_unique'),
                    ),
            ],
        ),
    ]
