# Generated by Django 3.1.14 on 2022-08-12 09:36

from django.db import migrations, models

sql_query = "UPDATE tasks_task SET task_status = 'to_be_revised'  WHERE task_status = 'rejected';"
reverse_query = "UPDATE tasks_task SET task_status = 'rejected'  WHERE task_status = 'to_be_revised';"


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0030_auto_20220707_0959"),
    ]

    operations = [
        migrations.RunSQL(
            sql=sql_query,
            reverse_sql=reverse_query,
        ),
        migrations.AlterField(
            model_name="task",
            name="task_status",
            field=models.CharField(
                choices=[
                    ("unlabeled", "unlabeled"),
                    ("labeled", "labeled"),
                    ("skipped", "skipped"),
                    ("accepted", "accepted"),
                    ("accepted_with_changes", "accepted_with_changes"),
                    ("freezed", "freezed"),
                    ("to_be_revised", "to_be_revised"),
                    ("draft", "draft"),
                ],
                default="unlabeled",
                max_length=100,
                verbose_name="task_status",
            ),
        ),
    ]
