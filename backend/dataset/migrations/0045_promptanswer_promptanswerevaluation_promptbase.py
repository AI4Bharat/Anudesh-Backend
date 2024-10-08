# Generated by Django 3.2.14 on 2024-01-01 16:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0044_instructions_interactions"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromptAnswer",
            fields=[
                (
                    "datasetbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="dataset.datasetbase",
                    ),
                ),
                (
                    "prompt",
                    models.TextField(
                        blank=True,
                        help_text="Prompt of the conversation",
                        null=True,
                        verbose_name="prompt",
                    ),
                ),
                (
                    "output",
                    models.TextField(
                        blank=True,
                        help_text="Response of the conversation",
                        null=True,
                        verbose_name="response",
                    ),
                ),
                (
                    "model",
                    models.CharField(
                        choices=[
                            ("GPT3.5", "GPT3.5"),
                            ("GPT4", "GPT4"),
                            ("LLAMA2", "LLAMA2"),
                        ],
                        help_text="Model of the response",
                        max_length=16,
                        verbose_name="model",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[
                            ("English", "English"),
                            ("Assamese", "Assamese"),
                            ("Bengali", "Bengali"),
                            ("Bodo", "Bodo"),
                            ("Dogri", "Dogri"),
                            ("Gujarati", "Gujarati"),
                            ("Hindi", "Hindi"),
                            ("Kannada", "Kannada"),
                            ("Kashmiri", "Kashmiri"),
                            ("Konkani", "Konkani"),
                            ("Maithili", "Maithili"),
                            ("Malayalam", "Malayalam"),
                            ("Manipuri", "Manipuri"),
                            ("Marathi", "Marathi"),
                            ("Nepali", "Nepali"),
                            ("Odia", "Odia"),
                            ("Punjabi", "Punjabi"),
                            ("Sanskrit", "Sanskrit"),
                            ("Santali", "Santali"),
                            ("Sindhi", "Sindhi"),
                            ("Sinhala", "Sinhala"),
                            ("Tamil", "Tamil"),
                            ("Telugu", "Telugu"),
                            ("Urdu", "Urdu"),
                        ],
                        max_length=15,
                        verbose_name="language",
                    ),
                ),
            ],
            bases=("dataset.datasetbase",),
        ),
        migrations.CreateModel(
            name="PromptBase",
            fields=[
                (
                    "datasetbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="dataset.datasetbase",
                    ),
                ),
                (
                    "prompt",
                    models.TextField(
                        blank=True,
                        help_text="Prompt of the conversation",
                        null=True,
                        verbose_name="prompt",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[
                            ("English", "English"),
                            ("Assamese", "Assamese"),
                            ("Bengali", "Bengali"),
                            ("Bodo", "Bodo"),
                            ("Dogri", "Dogri"),
                            ("Gujarati", "Gujarati"),
                            ("Hindi", "Hindi"),
                            ("Kannada", "Kannada"),
                            ("Kashmiri", "Kashmiri"),
                            ("Konkani", "Konkani"),
                            ("Maithili", "Maithili"),
                            ("Malayalam", "Malayalam"),
                            ("Manipuri", "Manipuri"),
                            ("Marathi", "Marathi"),
                            ("Nepali", "Nepali"),
                            ("Odia", "Odia"),
                            ("Punjabi", "Punjabi"),
                            ("Sanskrit", "Sanskrit"),
                            ("Santali", "Santali"),
                            ("Sindhi", "Sindhi"),
                            ("Sinhala", "Sinhala"),
                            ("Tamil", "Tamil"),
                            ("Telugu", "Telugu"),
                            ("Urdu", "Urdu"),
                        ],
                        max_length=15,
                        verbose_name="language",
                    ),
                ),
                (
                    "instruction_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="dataset.instructions",
                    ),
                ),
            ],
            bases=("dataset.datasetbase",),
        ),
        migrations.CreateModel(
            name="PromptAnswerEvaluation",
            fields=[
                (
                    "datasetbase_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="dataset.datasetbase",
                    ),
                ),
                (
                    "output_likert_score",
                    models.IntegerField(
                        blank=True,
                        help_text="Rating of the prompt response",
                        null=True,
                        verbose_name="prompt_response_rating",
                    ),
                ),
                (
                    "form_output_json",
                    models.JSONField(
                        blank=True,
                        help_text="Form output of the prompt response (JSON)",
                        null=True,
                        verbose_name="form_output",
                    ),
                ),
                (
                    "datetime",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date and time of the prompt response",
                        null=True,
                        verbose_name="datetime",
                    ),
                ),
                (
                    "time_taken",
                    models.FloatField(
                        blank=True,
                        help_text="Time taken to complete the prompt response",
                        null=True,
                        verbose_name="time_taken",
                    ),
                ),
                (
                    "model_output_id",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="dataset.promptanswer",
                    ),
                ),
            ],
            bases=("dataset.datasetbase",),
        ),
    ]
