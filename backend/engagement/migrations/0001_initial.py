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
                        name='Favorite',
                        fields=[
                            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                            ('created_at', models.DateTimeField(auto_now_add=True)),
                            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                            ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='listings.listing')),
                        ],
                        options={
                            "db_table": "listings_favorite",
                            'ordering': ('-created_at', '-pk'),
                        },
                    ),
                migrations.CreateModel(
                        name='SavedSearch',
                        fields=[
                            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                            ('name', models.CharField(max_length=80)),
                            ('filters', models.JSONField(default=dict)),
                            ('active', models.BooleanField(default=True)),
                            ('frequency', models.CharField(choices=[('immediate', 'Immediate'), ('daily', 'Daily')], default='daily', max_length=12)),
                            ('version', models.PositiveIntegerField(default=1)),
                            ('created_at', models.DateTimeField(auto_now_add=True)),
                            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                        ],
                        options={
                            "db_table": "listings_savedsearch",
                            'ordering': ('-created_at', '-pk'),
                        },
                    ),
                migrations.AddConstraint(
                        model_name='favorite',
                        constraint=models.UniqueConstraint(fields=('user', 'listing'), name='listing_favorite_unique'),
                    ),
                migrations.CreateModel(
                        name="ShopFollow",
                        fields=[
                            (
                                "id",
                                models.BigAutoField(
                                    auto_created=True,
                                    primary_key=True,
                                    serialize=False,
                                    verbose_name="ID",
                                ),
                            ),
                            ("created_at", models.DateTimeField(auto_now_add=True)),
                            (
                                "shop",
                                models.ForeignKey(
                                    on_delete=django.db.models.deletion.CASCADE,
                                    related_name="followers",
                                    to="shops.shop",
                                ),
                            ),
                            (
                                "user",
                                models.ForeignKey(
                                    on_delete=django.db.models.deletion.CASCADE,
                                    related_name="shop_follows",
                                    to=settings.AUTH_USER_MODEL,
                                ),
                            ),
                        ],
                        options={
                            "db_table": "shops_shopfollow",
                            "ordering": ("-created_at", "-pk"),
                            "constraints": [
                                models.UniqueConstraint(
                                    fields=("user", "shop"), name="shop_follow_unique"
                                )
                            ],
                        },
                    ),
            ],
        ),
    ]
