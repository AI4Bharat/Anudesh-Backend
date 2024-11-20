# Generated by Django 3.2.14 on 2024-10-29 09:02

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0049_annotation_meta_stats"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="annotation",
            unique_together={("task", "completed_by", "parent_annotation")},
        ),
    ]