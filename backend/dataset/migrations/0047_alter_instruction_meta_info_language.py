# Generated by Django 3.2.14 on 2024-01-10 07:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dataset", "0046_auto_20240104_0617"),
    ]

    operations = [
        migrations.AlterField(
            model_name="instruction",
            name="meta_info_language",
            field=models.CharField(
                blank=True,
                choices=[
                    ("1", "English(Any script)"),
                    ("2", "Indic(Indic script)"),
                    ("3", "Indic(Latin script)"),
                    ("4", "Indic/English(Latin script)"),
                ],
                help_text="Language of the instruction",
                max_length=20,
                null=True,
                verbose_name="Meta Info Language",
            ),
        ),
    ]
