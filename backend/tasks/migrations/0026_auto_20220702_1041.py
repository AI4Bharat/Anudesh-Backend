# Generated by Django 3.1.14 on 2022-07-02 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0025_alter_tasklock_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tasklock',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]