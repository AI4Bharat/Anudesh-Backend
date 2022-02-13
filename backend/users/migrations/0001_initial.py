# Generated by Django 3.2.12 on 2022-02-08 10:18

from django.db import migrations, models
import django.utils.timezone
import users.utils


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("username", models.CharField(max_length=265, verbose_name="username")),
                (
                    "email",
                    models.EmailField(
                        max_length=254, unique=True, verbose_name="email_address"
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=265, verbose_name="first_name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=265, verbose_name="last_name"
                    ),
                ),
                (
                    "phone",
                    models.CharField(blank=True, max_length=256, verbose_name="phone"),
                ),
                (
                    "profile_photo",
                    models.ImageField(blank=True, upload_to=users.utils.hash_upload),
                ),
                (
                    "role",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Annotator"),
                            (2, "Workspace Manager"),
                            (3, "Organization Owner"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether to treat this user as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                (
                    "activity_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="last annotation activity"
                    ),
                ),
                (
                    "invite_accepted",
                    models.BooleanField(default=False, verbose_name="invite_accepted"),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "db_table": "user",
            },
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["username"], name="user_usernam_b79065_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["email"], name="user_email_7bbb4c_idx"),
        ),
    ]
