# Generated by Django 3.2.16 on 2023-01-13 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dataset", "0035_speechconversation_prediction_json"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sentencetext",
            name="domain",
            field=models.CharField(
                choices=[
                    ("None", "None"),
                    ("General", "General"),
                    ("News", "News"),
                    ("Education", "Education"),
                    ("Legal", "Legal"),
                    ("Government-Press-Release", "Government-Press-Release"),
                    ("Healthcare", "Healthcare"),
                    ("Agriculture", "Agriculture"),
                    ("Automobile", "Automobile"),
                    ("Tourism", "Tourism"),
                    ("Financial", "Financial"),
                    ("Movies", "Movies"),
                    ("Subtitles", "Subtitles"),
                    ("Sports", "Sports"),
                    ("Technology", "Technology"),
                    ("Lifestyle", "Lifestyle"),
                    ("Entertainment", "Entertainment"),
                    ("Parliamentary", "Parliamentary"),
                    ("Art-and-Culture", "Art-and-Culture"),
                    ("Economy", "Economy"),
                    ("History", "History"),
                    ("Philosophy", "Philosophy"),
                    ("Religion", "Religion"),
                    ("National-Security-and-Defence", "National-Security-and-Defence"),
                    ("Literature", "Literature"),
                    ("Geography", "Geography"),
                ],
                default="None",
                help_text="Domain of the Sentence",
                max_length=1024,
                verbose_name="domain",
            ),
        ),
    ]