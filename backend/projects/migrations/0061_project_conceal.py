# Generated by Django 3.2.14 on 2025-01-09 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0060_auto_20241029_0902'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='conceal',
            field=models.BooleanField(default=False, help_text='To hide annotator,reviewer and superchecker details.', verbose_name='conceal'),
        ),
    ]
