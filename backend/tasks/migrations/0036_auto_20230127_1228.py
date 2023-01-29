# Generated by Django 3.2.16 on 2023-01-27 12:28


from django.db import migrations, models
from projects.utils import no_of_words
from dataset.models import DatasetInstance
from dataset import models as dataset_models


def add_word_count(apps, schema_editor):
    tasks = apps.get_model("tasks", "Task")
    db_alias = schema_editor.connection.alias
    taskobj = tasks.objects.using(db_alias).all()
    for tas in taskobj:
        try:
            if "word_count" in tas.data.keys():
                pass
            else:
                if "input_text" in tas.data.keys():
                    try:
                        tas.data["word_count"] = no_of_words(tas.data["input_text"])
                    except TypeError:
                        pass
                    except:
                        tas.data["word_count"] = 0
                    tas.save()
                elif "text" in tas.data.keys():
                    try:
                        tas.data["word_count"] = no_of_words(tas.data["text"])
                    except TypeError:
                        pass
                    except:
                        tas.data["word_count"] = 0
                    tas.save()
        except:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0035_auto_20230127_1226"),
    ]

    operations = [
        migrations.RunPython(add_word_count),
    ]
