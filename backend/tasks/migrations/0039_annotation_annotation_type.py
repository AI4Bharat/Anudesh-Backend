# Generated by Django 3.2.14 on 2023-03-16 04:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0038_auto_20230313_1354"),
    ]

    operations = [
        migrations.AddField(
            model_name="annotation",
            name="annotation_type",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Annotator's Annotation"),
                    (2, "Reviewer's Annotation"),
                    (3, "Super Checker's Annotation"),
                ],
                default=1,
            ),
        ),
    ]
