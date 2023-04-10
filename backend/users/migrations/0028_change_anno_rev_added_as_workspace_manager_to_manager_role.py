# Generated by Django 3.2.14 on 2023-04-03 08:00

from django.db import migrations
from workspaces.models import Workspace
from users.models import User


def change_annotator_reviewer_added_as_workspace_manager_to_manager_role(
    apps, schema_editor
):
    workspaces = Workspace.objects.all()
    users_list = []
    for workspace in workspaces:
        for manager in workspace.managers.all():
            if (manager.role == User.ANNOTATOR) or (manager.role == User.REVIEWER):
                setattr(manager, "role", User.WORKSPACE_MANAGER)
                users_list.append(manager)

    User.objects.bulk_update(users_list, ["role"], 512)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0027_change_users_having_superuser_status_to_admin_role"),
    ]

    operations = [
        migrations.RunPython(
            change_annotator_reviewer_added_as_workspace_manager_to_manager_role
        ),
    ]
