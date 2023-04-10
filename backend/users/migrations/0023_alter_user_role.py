# Generated by Django 3.2.14 on 2023-03-13 08:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0022_data_migration_roles_rework"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "Annotator"),
                    (2, "Reviewer"),
                    (3, "Super Checker"),
                    (4, "Workspace Manager"),
                    (5, "Organization Owner"),
                    (6, "Admin"),
                ],
                default=1,
            ),
        ),
    ]