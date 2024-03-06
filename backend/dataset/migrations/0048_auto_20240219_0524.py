# Generated by Django 3.2.14 on 2024-02-19 05:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0047_alter_instruction_meta_info_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="promptanswer",
            name="eval_form_output_json",
            field=models.JSONField(
                blank=True,
                help_text="Form output of the prompt response (JSON)",
                null=True,
                verbose_name="evaluation_form_output",
            ),
        ),
        migrations.AddField(
            model_name="promptanswer",
            name="eval_output_likert_score",
            field=models.IntegerField(
                blank=True,
                help_text="Rating of the prompt response",
                null=True,
                verbose_name="evaluation_prompt_response_rating",
            ),
        ),
        migrations.AddField(
            model_name="promptanswer",
            name="eval_time_taken",
            field=models.FloatField(
                blank=True,
                help_text="Time taken to complete the prompt response",
                null=True,
                verbose_name="evaluation_time_taken",
            ),
        ),
        migrations.AddField(
            model_name="promptanswer",
            name="interaction_id",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="dataset.interaction",
            ),
        ),
    ]
