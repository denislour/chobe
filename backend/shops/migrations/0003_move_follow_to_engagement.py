from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("shops", "0002_shopfollow"),
        ("engagement", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="ShopFollow")],
        ),
    ]
