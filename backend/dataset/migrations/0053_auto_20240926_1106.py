# Generated by Django 3.2.14 on 2024-09-26 11:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0052_auto_20240910_0726"),
    ]

    operations = [
        migrations.AlterField(
            model_name="instruction",
            name="meta_info_model",
            field=models.CharField(
                choices=[
                    ("GPT3.5", "GPT3.5"),
                    ("GPT4", "GPT4"),
                    ("LLAMA2", "LLAMA2"),
                    ("GPT4OMini", "GPT4OMini"),
                    ("GPT4O", "GPT4O"),
                    ("GEMMA", "GEMMA"),
                ],
                default="GPT3.5",
                help_text="Model information for the instruction",
                max_length=255,
                verbose_name="Meta Info Model",
            ),
        ),
        migrations.AlterField(
            model_name="interaction",
            name="datetime",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp of the interaction",
                null=True,
                verbose_name="Datetime",
            ),
        ),
        migrations.AlterField(
            model_name="interaction",
            name="instruction_id",
            field=models.ForeignKey(
                blank=True,
                help_text="ID of the related instruction",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="dataset.instruction",
                verbose_name="Instruction ID",
            ),
        ),
        migrations.AlterField(
            model_name="promptanswer",
            name="model",
            field=models.CharField(
                choices=[
                    ("GPT3.5", "GPT3.5"),
                    ("GPT4", "GPT4"),
                    ("LLAMA2", "LLAMA2"),
                    ("GPT4OMini", "GPT4OMini"),
                    ("GPT4O", "GPT4O"),
                    ("GEMMA", "GEMMA"),
                ],
                help_text="Model of the response",
                max_length=16,
                verbose_name="model",
            ),
        ),
    ]