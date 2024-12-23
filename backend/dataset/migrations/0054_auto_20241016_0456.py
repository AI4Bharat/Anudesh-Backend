# Generated by Django 3.2.14 on 2024-10-16 04:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0053_auto_20240926_1106"),
    ]

    operations = [
        migrations.CreateModel(
            name="MultiModelInteraction",
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
                    "parent_interaction_ids",
                    models.JSONField(
                        blank=True,
                        help_text="A json containing all the parent ids",
                        null=True,
                        verbose_name="Parent Interaction Ids",
                    ),
                ),
                (
                    "multiple_interaction_json",
                    models.JSONField(
                        help_text="A json containing interactions for a single prompt from multiple models.",
                        verbose_name="Multiple Interaction Json",
                    ),
                ),
                (
                    "eval_form_json",
                    models.JSONField(
                        blank=True,
                        help_text="Form output for all the interactions",
                        null=True,
                        verbose_name="form_output",
                    ),
                ),
                (
                    "no_of_turns",
                    models.IntegerField(
                        blank=True,
                        help_text="Number of turns in the interaction",
                        null=True,
                        verbose_name="Number of Turns",
                    ),
                ),
                (
                    "no_of_models",
                    models.IntegerField(
                        blank=True,
                        help_text="Number of models in the interaction",
                        null=True,
                        verbose_name="Number of Models",
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
                        help_text="Language of the interaction",
                        max_length=20,
                        verbose_name="Language",
                    ),
                ),
                (
                    "datetime",
                    models.DateTimeField(
                        blank=True,
                        help_text="Timestamp of the interaction",
                        null=True,
                        verbose_name="Datetime",
                    ),
                ),
            ],
            bases=("dataset.datasetbase",),
        ),
        migrations.AlterField(
            model_name="datasetinstance",
            name="dataset_type",
            field=models.CharField(
                choices=[
                    ("SentenceText", "SentenceText"),
                    ("TranslationPair", "TranslationPair"),
                    ("OCRDocument", "OCRDocument"),
                    ("BlockText", "BlockText"),
                    ("Conversation", "Conversation"),
                    ("SpeechConversation", "SpeechConversation"),
                    ("PromptBase", "PromptBase"),
                    ("PromptAnswer", "PromptAnswer"),
                    ("PromptAnswerEvaluation", "PromptAnswerEvaluation"),
                    ("Interaction", "Interaction"),
                    ("Instruction", "Instruction"),
                    ("MultiModelInteraction", "MultiModelInteraction"),
                ],
                help_text="Dataset Type which is specific for each annotation task",
                max_length=100,
                verbose_name="dataset_type",
            ),
        ),
    ]
