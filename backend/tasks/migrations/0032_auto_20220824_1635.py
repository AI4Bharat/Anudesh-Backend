# Generated by Django 3.1.14 on 2022-08-24 16:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0031_auto_20220812_0936'),
    ]

    operations = [
        migrations.AddField(
            model_name='annotation',
            name='annotation_status',
            field=models.CharField(choices=[('unlabeled', 'unlabeled'), ('labeled', 'labeled'), ('skipped', 'skipped'), ('draft', 'draft')], default='unlabeled', max_length=100, verbose_name='annotation_status'),
        ),
        migrations.AlterField(
            model_name='task',
            name='task_status',
            field=models.CharField(choices=[('incomplete', 'incomplete'), ('complete', 'complete'), ('accepted', 'accepted'), ('accepted_with_changes', 'accepted_with_changes'), ('freezed', 'freezed'), ('to_be_revised', 'to_be_revised')], default='incomplete', max_length=100, verbose_name='task_status'),
        ),
    ]