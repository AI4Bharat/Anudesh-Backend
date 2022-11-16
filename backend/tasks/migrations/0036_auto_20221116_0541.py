# Generated by Django 3.2.14 on 2022-11-16 05:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0035_auto_20221107_0539'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annotation',
            name='annotation_status',
            field=models.CharField(choices=[('unlabeled', 'unlabeled'), ('labeled', 'labeled'), ('skipped', 'skipped'), ('draft', 'draft'), ('unreviewed', 'unreviewed'), ('accepted', 'accepted'), ('to_be_revised', 'to_be_revised'), ('accepted_with_minor_changes', 'accepted_with_minor_changes'), ('accepted_with_major_changes', 'accepted_with_major_changes')], default='unlabeled', max_length=100, verbose_name='annotation_status'),
        ),
        migrations.AlterField(
            model_name='task',
            name='task_status',
            field=models.CharField(choices=[('incomplete', 'incomplete'), ('annotated', 'annotated'), ('reviewed', 'reviewed'), ('Exported', 'Exported'), ('freezed', 'freezed')], default='unlabeled', max_length=100, verbose_name='task_status'),
        ),
    ]
