from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("webcall", "0002_add_updated_at"),  # Replace with your last migration name
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="last_active",
            field=models.DateTimeField(
                default=django.utils.timezone.now, null=True, blank=True
            ),
        ),
    ]
