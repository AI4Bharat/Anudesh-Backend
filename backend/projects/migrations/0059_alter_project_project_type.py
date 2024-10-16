# Generated by Django 3.2.14 on 2024-10-16 04:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0058_rename_max_pull_count_per_user_project_max_tasks_per_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="project_type",
            field=models.CharField(
                choices=[
                    ("ModelOutputEvaluation", "ModelOutputEvaluation"),
                    ("ModelInteractionEvaluation", "ModelInteractionEvaluation"),
                    ("MultipleInteractionEvaluation", "MultipleInteractionEvaluation"),
                    ("InstructionDrivenChat", "InstructionDrivenChat"),
                ],
                help_text="Project Type indicating the annotation task",
                max_length=100,
            ),
        ),
    ]