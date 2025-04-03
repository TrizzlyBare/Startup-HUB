from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authen", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="bio",
            field=models.TextField(
                blank=True,
                help_text="A short description about yourself",
                max_length=500,
                null=True,
                verbose_name="bio",
            ),
        ),
    ]
