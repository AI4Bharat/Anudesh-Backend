# Generated by Django 3.2.14 on 2024-12-23 04:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataset', '0055_auto_20241029_0902'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interaction',
            name='language',
            field=models.CharField(choices=[('English', 'English'), ('Assamese', 'Assamese'), ('Bengali', 'Bengali'), ('Burmese', 'Burmese'), ('Bodo', 'Bodo'), ('Dogri', 'Dogri'), ('Gujarati', 'Gujarati'), ('Hindi', 'Hindi'), ('Kannada', 'Kannada'), ('Kashmiri', 'Kashmiri'), ('Konkani', 'Konkani'), ('Maithili', 'Maithili'), ('Malayalam', 'Malayalam'), ('Manipuri', 'Manipuri'), ('Marathi', 'Marathi'), ('Nepali', 'Nepali'), ('Odia', 'Odia'), ('Punjabi', 'Punjabi'), ('Sanskrit', 'Sanskrit'), ('Santali', 'Santali'), ('Sindhi', 'Sindhi'), ('Sinhala', 'Sinhala'), ('Tamil', 'Tamil'), ('Telugu', 'Telugu'), ('Thai', 'Thai'), ('Urdu', 'Urdu')], help_text='Language of the interaction', max_length=20, verbose_name='Language'),
        ),
        migrations.AlterField(
            model_name='multimodelinteraction',
            name='language',
            field=models.CharField(choices=[('English', 'English'), ('Assamese', 'Assamese'), ('Bengali', 'Bengali'), ('Burmese', 'Burmese'), ('Bodo', 'Bodo'), ('Dogri', 'Dogri'), ('Gujarati', 'Gujarati'), ('Hindi', 'Hindi'), ('Kannada', 'Kannada'), ('Kashmiri', 'Kashmiri'), ('Konkani', 'Konkani'), ('Maithili', 'Maithili'), ('Malayalam', 'Malayalam'), ('Manipuri', 'Manipuri'), ('Marathi', 'Marathi'), ('Nepali', 'Nepali'), ('Odia', 'Odia'), ('Punjabi', 'Punjabi'), ('Sanskrit', 'Sanskrit'), ('Santali', 'Santali'), ('Sindhi', 'Sindhi'), ('Sinhala', 'Sinhala'), ('Tamil', 'Tamil'), ('Telugu', 'Telugu'), ('Thai', 'Thai'), ('Urdu', 'Urdu')], help_text='Language of the interaction', max_length=20, verbose_name='Language'),
        ),
    ]
