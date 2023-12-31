# Generated by Django 3.2.14 on 2022-11-12 03:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0032_alter_datasetbase_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpeechConversation",
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
                    "domain",
                    models.CharField(
                        blank=True,
                        help_text="Domain of the speech conversation",
                        max_length=1024,
                        null=True,
                        verbose_name="domain",
                    ),
                ),
                (
                    "scenario",
                    models.TextField(
                        blank=True,
                        help_text="Scenario of the conversation",
                        null=True,
                        verbose_name="scenario",
                    ),
                ),
                (
                    "speaker_count",
                    models.IntegerField(
                        help_text="Number of speakers involved in conversation",
                        verbose_name="speaker_count",
                    ),
                ),
                (
                    "speakers_json",
                    models.JSONField(
                        blank=True,
                        help_text="Details of the speakers involved in the conversation",
                        null=True,
                        verbose_name="speakers_details",
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
                    "transcribed_json",
                    models.JSONField(
                        blank=True,
                        help_text="Conversation data comprising speaker_id and sentence/sentences",
                        null=True,
                        verbose_name="transcribed_json",
                    ),
                ),
                (
                    "machine_transcribed_json",
                    models.JSONField(
                        blank=True,
                        help_text="Machine Transcribed output of conversation data, in same format as of transcribed_json",
                        null=True,
                        verbose_name="machine_transcribed_json",
                    ),
                ),
                (
                    "audio_url",
                    models.URLField(
                        blank=True,
                        help_text="Link to the audio-file",
                        null=True,
                        verbose_name="audio_url",
                    ),
                ),
                (
                    "audio_duration",
                    models.FloatField(
                        blank=True,
                        help_text="Length of the audio in seconds (float)",
                        null=True,
                        verbose_name="audio_play_duration",
                    ),
                ),
                (
                    "reference_raw_transcript",
                    models.TextField(
                        blank=True,
                        help_text="Optional field to store the plaintext transcription which was used by the speaker to read out",
                        null=True,
                        verbose_name="reference_raw_transcript",
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
                ],
                help_text="Dataset Type which is specific for each annotation task",
                max_length=100,
                verbose_name="dataset_type",
            ),
        ),
    ]
