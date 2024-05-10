# Generated by Django 3.2.14 on 2024-04-26 05:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0034_user_notification_limit"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="invited_by",
            field=models.ForeignKey(
                blank=True,
                default=2,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="is_approved",
            field=models.BooleanField(
                default=True,
                help_text="Indicates whether user is approved by the admin or not.",
                verbose_name="is_approved",
            ),
        ),
    ]