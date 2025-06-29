import json
from collections import OrderedDict
from datetime import datetime
from time import sleep
import pandas as pd
import ast
import math

from django.core.files import File
from django.db import IntegrityError
from django.db.models import Count, Q, F, Case, When, OuterRef, Exists, Subquery, IntegerField
from django.forms.models import model_to_dict
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import LANG_CHOICES
from users.serializers import UserEmailSerializer
from dataset.serializers import TaskResultSerializer, DatasetInstanceSerializer
from utils.search import process_search_query
from django_celery_results.models import TaskResult
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from users.models import User

import ast
from projects.serializers import (
    ProjectSerializer,
    ProjectUsersSerializer,
    ProjectSerializerOptimized,
)

from tasks.models import Annotation as Annotation_model
from tasks.models import *
from tasks.models import Task
from tasks.serializers import TaskSerializer
from .models import *
from .registry_helper import ProjectRegistry
from dataset import models as dataset_models
import notifications

from .utils import (
    get_annotations_for_project,
    get_status_from_query_params,
    get_task_ids,
    get_user_from_query_params,
    ocr_word_count,
    get_attributes_for_ModelInteractionEvaluation,
    filter_tasks_for_review_filter_criteria,
    add_extra_task_data,
    validate_metadata_json_format,
)

from dataset.models import DatasetInstance

# Import celery tasks
from .tasks import (
    create_parameters_for_task_creation,
    add_new_data_items_into_project,
    export_project_in_place,
    export_project_new_record,
    filter_data_items,
)

from .decorators import (
    is_organization_owner_or_workspace_manager,
    is_project_editor,
    project_is_archived,
    project_is_published,
)
from .utils import (
    is_valid_date,
    no_of_words,
    minor_major_accepted_task,
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
    get_audio_segments_count,
    calculate_word_error_rate_between_two_llm_prompts,
)

from workspaces.decorators import is_particular_workspace_manager
from users.utils import generate_random_string
from notifications.views import createNotification
from notifications.utils import get_userids_from_project_id

# Create your views here.

EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

PROJECT_IS_PUBLISHED_ERROR = {"message": "This project is already published!"}


def get_task_field(annotation_json, field):
    return annotation_json[field]


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]


def get_review_reports(proj_id, userid, start_date, end_date):
    user = User.objects.get(id=userid)
    userName = user.username
    email = user.email
    project_obj = Project.objects.get(id=proj_id)
    proj_type = project_obj.project_type
    proj_type_lower = proj_type.lower()
    is_translation_project = True if "translation" in proj_type_lower else False
    total_tasks = Task.objects.filter(project_id=proj_id, review_user=userid)

    if user in project_obj.frozen_users.all():
        userName = userName + "*"

    total_task_count = total_tasks.count()

    accepted_objs = Annotation_model.objects.filter(
        annotation_status="accepted",
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    accepted_objs_count = accepted_objs.count()

    superchecked_accepted_annos = Annotation_model.objects.filter(
        parent_annotation_id__in=accepted_objs,
        annotation_status__in=[
            VALIDATED,
            VALIDATED_WITH_CHANGES,
        ],
    )

    superchecked_accepted_annos_count = superchecked_accepted_annos.count()

    accepted_objs_only = accepted_objs_count - superchecked_accepted_annos_count

    minor_changes = Annotation_model.objects.filter(
        annotation_status="accepted_with_minor_changes",
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    minor_changes_count = minor_changes.count()

    superchecked_minor_annos = Annotation_model.objects.filter(
        parent_annotation_id__in=minor_changes,
        annotation_status__in=[
            VALIDATED,
            VALIDATED_WITH_CHANGES,
        ],
    )

    superchecked_minor_annos_count = superchecked_minor_annos.count()

    minor_changes_only = minor_changes_count - superchecked_minor_annos_count

    major_changes = Annotation_model.objects.filter(
        annotation_status="accepted_with_major_changes",
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    major_changes_count = major_changes.count()
    # minor_changes, major_changes = minor_major_accepted_task(acceptedwtchange_objs)

    superchecked_major_annos = Annotation_model.objects.filter(
        parent_annotation_id__in=major_changes,
        annotation_status__in=[
            VALIDATED,
            VALIDATED_WITH_CHANGES,
        ],
    )

    superchecked_major_annos_count = superchecked_major_annos.count()

    major_changes_only = major_changes_count - superchecked_major_annos_count

    unreviewed_count = Annotation_model.objects.filter(
        annotation_status="unreviewed",
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    ).count()

    draft_count = Annotation_model.objects.filter(
        annotation_status="draft",
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    ).count()

    skipped_count = Annotation_model.objects.filter(
        annotation_status="skipped",
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    ).count()

    to_be_revised_tasks_count = Annotation_model.objects.filter(
        annotation_status="to_be_revised",
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    ).count()

    total_rev_annos = Annotation_model.objects.filter(
        task__project_id=proj_id,
        task__review_user=userid,
        annotation_type=REVIEWER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    total_rev_sup_annos = Annotation_model.objects.filter(
        parent_annotation__in=total_rev_annos
    )

    total_reviewed_annos = total_rev_annos.filter(task__task_status="reviewed")

    total_superchecked_annos = total_rev_sup_annos.filter(
        task__task_status="super_checked"
    )

    total_rejection_loop_value_list = [
        anno.task.revision_loop_count["super_check_count"]
        for anno in total_rev_sup_annos
    ]
    if len(total_rejection_loop_value_list) > 0:
        avg_rejection_loop_value = sum(total_rejection_loop_value_list) / len(
            total_rejection_loop_value_list
        )
    else:
        avg_rejection_loop_value = 0
    tasks_rejected_max_times = 0
    for anno in total_rev_sup_annos:
        if (
            anno.task.revision_loop_count["super_check_count"]
            >= project_obj.revision_loop_count
        ):
            tasks_rejected_max_times += 1

    total_rev_annos_accepted = total_rev_annos.filter(
        annotation_status__in=[
            ACCEPTED,
            ACCEPTED_WITH_MINOR_CHANGES,
            ACCEPTED_WITH_MAJOR_CHANGES,
        ]
    )
    total_audio_duration_list = []
    total_raw_audio_duration_list = []
    total_word_count_list = []
    total_word_error_rate_rs_list = []
    total_word_error_rate_ar_list = []
    if is_translation_project or proj_type == "SemanticTextualSimilarity_Scale5":
        for anno in total_rev_annos_accepted:
            try:
                total_word_count_list.append(anno.task.data["word_count"])
            except:
                pass
    elif proj_type == "OCRTranscriptionEditing":
        for anno in total_rev_annos_accepted:
            total_word_count_list.append(ocr_word_count(anno.result))
    elif proj_type in get_audio_project_types():
        for anno in total_rev_annos_accepted:
            try:
                total_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
                total_raw_audio_duration_list.append(anno.task.data["audio_duration"])
            except:
                pass
        for anno in total_superchecked_annos:
            try:
                total_word_error_rate_rs_list.append(
                    calculate_word_error_rate_between_two_llm_prompts(
                        anno.result, anno.parent_annotation.result
                    )
                )
            except:
                pass
        for anno in total_reviewed_annos:
            try:
                total_word_error_rate_ar_list.append(
                    calculate_word_error_rate_between_two_llm_prompts(
                        anno.result, anno.parent_annotation.result
                    )
                )
            except:
                pass

    total_word_count = sum(total_word_count_list)
    total_audio_duration = convert_seconds_to_hours(sum(total_audio_duration_list))
    total_raw_audio_duration = convert_seconds_to_hours(
        sum(total_raw_audio_duration_list)
    )
    if len(total_word_error_rate_rs_list) > 0:
        avg_word_error_rate_rs = sum(total_word_error_rate_rs_list) / len(
            total_word_error_rate_rs_list
        )
    else:
        avg_word_error_rate_rs = 0
    if len(total_word_error_rate_ar_list) > 0:
        avg_word_error_rate_ar = sum(total_word_error_rate_ar_list) / len(
            total_word_error_rate_ar_list
        )
    else:
        avg_word_error_rate_ar = 0

    if project_obj.project_stage > REVIEW_STAGE:
        annotations_of_superchecker_validated = Annotation_model.objects.filter(
            task__project_id=proj_id,
            annotation_status="validated",
            annotation_type=SUPER_CHECKER_ANNOTATION,
            parent_annotation__updated_at__range=[start_date, end_date],
        )
        parent_anno_ids = [
            ann.parent_annotation_id for ann in annotations_of_superchecker_validated
        ]
        accepted_validated_tasks = Annotation_model.objects.filter(
            id__in=parent_anno_ids,
            completed_by=userid,
        )

        annotations_of_superchecker_validated_with_changes = (
            Annotation_model.objects.filter(
                task__project_id=proj_id,
                annotation_status="validated_with_changes",
                annotation_type=SUPER_CHECKER_ANNOTATION,
                parent_annotation__updated_at__range=[start_date, end_date],
            )
        )
        parent_anno_ids = [
            ann.parent_annotation_id
            for ann in annotations_of_superchecker_validated_with_changes
        ]
        accepted_validated_with_changes_tasks = Annotation_model.objects.filter(
            id__in=parent_anno_ids,
            completed_by=userid,
        )

        annotations_of_superchecker_rejected = Annotation_model.objects.filter(
            task__project_id=proj_id,
            annotation_status="rejected",
            annotation_type=SUPER_CHECKER_ANNOTATION,
            parent_annotation__updated_at__range=[start_date, end_date],
        )
        parent_anno_ids = [
            ann.parent_annotation_id for ann in annotations_of_superchecker_rejected
        ]
        accepted_rejected_tasks = Annotation_model.objects.filter(
            id__in=parent_anno_ids, completed_by=userid, annotation_status="rejected"
        )

        result = {
            "Reviewer Name": userName,
            "Email": email,
            "Assigned": total_task_count,
            "Accepted": accepted_objs_only,
            "Accepted With Minor Changes": minor_changes_only,
            "Accepted With Major Changes": major_changes_only,
            "UnReviewed": unreviewed_count,
            "Draft": draft_count,
            "Skipped": skipped_count,
            "To Be Revised": to_be_revised_tasks_count,
            "Validated": accepted_validated_tasks.count(),
            "Validated With Changes": accepted_validated_with_changes_tasks.count(),
            "Rejected": accepted_rejected_tasks.count(),
            "Average Rejection Loop Value": round(avg_rejection_loop_value, 2),
            "Tasks Rejected Maximum Time": tasks_rejected_max_times,
        }

        if is_translation_project or proj_type in [
            "SemanticTextualSimilarity_Scale5",
            "OCRTranscriptionEditing",
            "OCRTranscription",
        ]:
            result["Total Word Count"] = total_word_count
        elif proj_type in get_audio_project_types():
            result["Total Segments Duration"] = total_audio_duration
            result["Total Raw Audio Duration"] = total_raw_audio_duration
            result["Average Word Error Rate R/S"] = round(avg_word_error_rate_rs, 2)
            result["Average Word Error Rate A/R"] = round(avg_word_error_rate_ar, 2)

        return result

    result = {
        "Reviewer Name": userName,
        "Email": email,
        "Assigned": total_task_count,
        "Accepted": accepted_objs_count,
        "Accepted With Minor Changes": minor_changes_count,
        "Accepted With Major Changes": major_changes_count,
        "UnReviewed": unreviewed_count,
        "Draft": draft_count,
        "Skipped": skipped_count,
        "To Be Revised": to_be_revised_tasks_count,
        "Average Rejection Loop Value": round(avg_rejection_loop_value, 2),
        "Tasks Rejected Maximum Time": tasks_rejected_max_times,
    }

    if is_translation_project or proj_type == "SemanticTextualSimilarity_Scale5":
        result["Total Word Count"] = total_word_count
    elif proj_type in get_audio_project_types():
        result["Total Segments Duration"] = total_audio_duration
        result["Total Raw Audio Duration"] = total_raw_audio_duration
        result["Average Word Error Rate R/S"] = round(avg_word_error_rate_rs, 2)
        result["Average Word Error Rate A/R"] = round(avg_word_error_rate_ar, 2)

    return result


def get_supercheck_reports(proj_id, userid, start_date, end_date):
    user = User.objects.get(id=userid)
    userName = user.username
    email = user.email
    project_obj = Project.objects.get(id=proj_id)
    proj_type = project_obj.project_type
    proj_type_lower = proj_type.lower()
    is_translation_project = True if "translation" in proj_type_lower else False
    total_tasks = Task.objects.filter(project_id=proj_id, super_check_user=userid)

    if user in project_obj.frozen_users.all():
        userName = userName + "*"

    total_task_count = total_tasks.count()

    validated_objs = Annotation_model.objects.filter(
        annotation_status="validated",
        task__project_id=proj_id,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    validated_objs_count = validated_objs.count()

    validated_with_changes_objs = Annotation_model.objects.filter(
        annotation_status="validated_with_changes",
        task__project_id=proj_id,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    validated_with_changes_objs_count = validated_with_changes_objs.count()

    unvalidated_objs = Annotation_model.objects.filter(
        annotation_status="unvalidated",
        task__project_id=proj_id,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    unvalidated_objs_count = unvalidated_objs.count()

    rejected_objs = Annotation_model.objects.filter(
        annotation_status="rejected",
        task__project_id=proj_id,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    rejected_objs_count = rejected_objs.count()

    skipped_objs = Annotation_model.objects.filter(
        annotation_status="skipped",
        task__project_id=proj_id,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    skipped_objs_count = skipped_objs.count()

    draft_objs = Annotation_model.objects.filter(
        annotation_status="draft",
        task__project_id=proj_id,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    draft_objs_count = draft_objs.count()

    total_sup_annos = Annotation_model.objects.filter(
        task__project_id=proj_id,
        task__super_check_user=userid,
        annotation_type=SUPER_CHECKER_ANNOTATION,
        updated_at__range=[start_date, end_date],
    )

    total_superchecked_annos = total_sup_annos.filter(task__task_status="super_checked")

    total_rejection_loop_value_list = [
        anno.task.revision_loop_count["super_check_count"] for anno in total_sup_annos
    ]
    if len(total_rejection_loop_value_list) > 0:
        avg_rejection_loop_value = sum(total_rejection_loop_value_list) / len(
            total_rejection_loop_value_list
        )
    else:
        avg_rejection_loop_value = 0
    tasks_rejected_max_times = 0
    for anno in total_sup_annos:
        if (
            anno.task.revision_loop_count["super_check_count"]
            >= project_obj.revision_loop_count
        ):
            tasks_rejected_max_times += 1

    validated_word_count_list = []
    validated_with_changes_word_count_list = []
    rejected_word_count_list = []
    validated_audio_duration_list = []
    validated_with_changes_audio_duration_list = []
    rejected_audio_duration_list = []
    total_word_error_rate_list = []
    total_raw_audio_duration_list = []
    if is_translation_project or proj_type == "SemanticTextualSimilarity_Scale5":
        for anno in validated_objs:
            try:
                validated_word_count_list.append(anno.task.data["word_count"])
            except:
                pass
        for anno in validated_with_changes_objs:
            try:
                validated_with_changes_word_count_list.append(
                    anno.task.data["word_count"]
                )
            except:
                pass
        for anno in rejected_objs:
            try:
                rejected_word_count_list.append(anno.task.data["word_count"])
            except:
                pass
    elif "OCRTranscription" in proj_type:
        for anno in validated_objs:
            validated_word_count_list.append(ocr_word_count(anno.result))
        for anno in validated_with_changes_objs:
            validated_with_changes_word_count_list.append(ocr_word_count(anno.result))
        for anno in rejected_objs:
            rejected_word_count_list.append(ocr_word_count(anno.result))
    elif proj_type in get_audio_project_types():
        for anno in validated_objs:
            try:
                validated_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
            except:
                pass
        for anno in validated_with_changes_objs:
            try:
                validated_with_changes_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
            except:
                pass
        for anno in rejected_objs:
            try:
                rejected_audio_duration_list.append(
                    get_audio_transcription_duration(anno.result)
                )
            except:
                pass
        for anno in total_sup_annos:
            try:
                total_raw_audio_duration_list.append(anno.task.data["audio_duration"])
            except:
                pass
        for anno in total_superchecked_annos:
            try:
                total_word_error_rate_list.append(
                    calculate_word_error_rate_between_two_llm_prompts(
                        anno.result, anno.parent_annotation.result
                    )
                )
            except:
                pass

    validated_word_count = sum(validated_word_count_list)
    validated_with_changes_word_count = sum(validated_with_changes_word_count_list)
    rejected_word_count = sum(rejected_word_count_list)
    validated_audio_duration = convert_seconds_to_hours(
        sum(validated_audio_duration_list)
    )
    validated_with_changes_audio_duration = convert_seconds_to_hours(
        sum(validated_with_changes_audio_duration_list)
    )
    rejected_audio_duration = convert_seconds_to_hours(
        sum(rejected_audio_duration_list)
    )
    total_raw_audio_duration = convert_seconds_to_hours(
        sum(total_raw_audio_duration_list)
    )
    if len(total_word_error_rate_list) > 0:
        avg_word_error_rate = sum(total_word_error_rate_list) / len(
            total_word_error_rate_list
        )
    else:
        avg_word_error_rate = 0

    result = {
        "SuperChecker Name": userName,
        "Email": email,
        "Assigned": total_task_count,
        "Validated": validated_objs_count,
        "Validated With Changes": validated_with_changes_objs_count,
        "UnValidated": unvalidated_objs_count,
        "Draft": draft_objs_count,
        "Skipped": skipped_objs_count,
        "Rejected": rejected_objs_count,
        "Average Rejection Loop Value": round(avg_rejection_loop_value, 2),
        "Tasks Rejected Maximum Time": tasks_rejected_max_times,
    }
    if is_translation_project or proj_type in [
        "SemanticTextualSimilarity_Scale5",
        "OCRTranscriptionEditing",
        "OCRTranscription",
    ]:
        result["Validated Word Count"] = validated_word_count
        result["Validated With Changes Word Count"] = validated_with_changes_word_count
        result["Rejected Word Count"] = rejected_word_count
    elif proj_type in get_audio_project_types():
        result["Validated Segments Duration"] = validated_audio_duration
        result["Validated With Changes Segments Duration"] = (
            validated_with_changes_audio_duration
        )
        result["Rejected Segments Duration"] = rejected_audio_duration
        result["Total Raw Audio Duration"] = total_raw_audio_duration
        result["Average Word Error Rate R/S"] = round(avg_word_error_rate, 2)

    return result


def extract_latest_status_date_time_from_taskresult_queryset(taskresult_queryset):
    """Function to extract the latest status and date time from the celery task results.

    Args:
        taskresult_queryset (Django Queryset): Celery task results queryset

    Returns:
        str: Complettion state of the latest celery task
        str: Complettion date of the latest celery task
        str: Complettion time of the latest celery task
    """

    # Sort the tasks by newest items first by date
    taskresult_queryset = taskresult_queryset.order_by("-date_done")

    # Get the export task status and last update date
    task_status = taskresult_queryset.first().as_dict()["status"]
    task_datetime = taskresult_queryset.first().as_dict()["date_done"]

    # Extract date and time from the datetime object
    task_date = task_datetime.date()
    task_time = f"{str(task_datetime.time().replace(microsecond=0))} UTC"

    return task_status, task_date, task_time


def get_project_pull_status(pk):
    """Function to return status of the last pull data items task.

    Args:
        pk (int): Primary key of the project

    Returns:
        str: Status of the project export
        str: Date when the last time project was exported
    """

    # Create the keyword argument for project ID
    project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'"

    # Check the celery project export status
    taskresult_queryset = TaskResult.objects.filter(
        task_name="projects.tasks.add_new_data_items_into_project",
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns
    if taskresult_queryset:
        # Sort the tasks by newest items first by date
        taskresult_queryset = taskresult_queryset.order_by("-date_done")

        # Get the export task status and last update date
        task_status = taskresult_queryset.first().as_dict()["status"]
        task_datetime = taskresult_queryset.first().as_dict()["date_done"]
        task_result = taskresult_queryset.first().as_dict()["result"]

        if '"' in task_result:
            task_result = task_result.strip('"')
        # Extract date and time from the datetime object
        task_date = task_datetime.date()
        task_time = f"{str(task_datetime.time().replace(microsecond=0))} UTC"

        return task_status, task_date, task_time, task_result
    return (
        "Success",
        "Synchronously Completed. No Date.",
        "Synchronously Completed. No Time.",
        "No result.",
    )


def get_project_export_status(pk):
    """Function to return status of the project export background task.

    Args:
        pk (int): Primary key of the project

    Returns:
        str: Status of the project export
        str: Date when the last time project was exported
    """

    # Create the keyword argument for project ID
    project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'" + ","

    # Check the celery project export status
    taskresult_queryset = TaskResult.objects.filter(
        task_name__in=[
            "projects.tasks.export_project_in_place",
            "projects.tasks.export_project_new_record",
        ],
        task_kwargs__contains=project_id_keyword_arg,
    )

    # If the celery TaskResults table returns
    if taskresult_queryset:
        return extract_latest_status_date_time_from_taskresult_queryset(
            taskresult_queryset
        )
    return (
        "Success",
        "Synchronously Completed. No Date.",
        "Synchronously Completed. No Time.",
    )


def get_task_creation_status(pk) -> str:
    """Function to return the status of the tasks of project that is queried.
    Args:
        pk (int): The primary key of the project
    Returns:
        str: Task Status
    """
    # Check the celery task creation status
    project_id_keyword_arg = "'project_id': " + str(pk)
    taskresult_queryset = TaskResult.objects.filter(
        task_name="projects.tasks.create_parameters_for_task_creation",
        task_kwargs__contains=project_id_keyword_arg,
    )
    task_creation_status_modified = {
        "PENDING": "Task Creation Process Pending",
        "RECEIVED": "Task Creation Process Received",
        "STARTED": "Task Creation Process Started",
        "SUCCESS": "Tasks Creation Process Successful",
        "FAILURE": "Task Creation Process Failed",
        "RETRY": "Task Creation Process Retried",
        "REVOKED": "Task Creation Process Revoked",
    }
    # If the celery TaskResults table returns
    if taskresult_queryset:
        task_creation_status = taskresult_queryset.first().as_dict()["status"]
        return task_creation_status_modified[task_creation_status]
    return ""


def get_project_creation_status(pk) -> str:
    # sourcery skip: use-named-expression
    """Function to return the status of the project that is queried.

    Args:
        pk (int): The primary key of the project

    Returns:
        str: Project Status
    """

    # Get the project object
    project = Project.objects.get(pk=pk)
    if project.is_archived:
        return "Archived"
    elif project.is_published:
        return "Published"
    else:
        return "Draft"


def get_task_count_unassigned(pk, user):
    project = Project.objects.get(pk=pk)
    required_annotators_per_task = project.required_annotators_per_task
    if required_annotators_per_task==1:
        proj_tasks = Task.objects.filter(project_id=pk).exclude(annotation_users=user)
        proj_tasks_unassigned = (
            proj_tasks.annotate(num_annotators=Count("annotation_users"))
        ).filter(num_annotators__lt=required_annotators_per_task)
        return len(proj_tasks_unassigned)
    
    if user.role==User.ADMIN:
        assigned_task_ids = Annotation_model.objects.filter(
        task__project_id=pk
        ).values_list("task_id", flat=True) 

        tasks = Task.objects.filter(
            project_id=pk,
            task_status__in=[INCOMPLETE]
        ).annotate(
            annotator_count=Count("annotation_users")
        ).filter(
            annotator_count__lt=project.required_annotators_per_task 
        ).exclude(id__in=assigned_task_ids)
        return tasks.count()

    else:
        #Tasks that the user has already worked on but are incomplete and yje pending task count of the user
        proj_annotations = Annotation_model.objects.filter(
            task__project_id=pk, 
            annotation_status=UNLABELED, 
            completed_by=user
        )
        annotation_tasks = proj_annotations.values_list("task_id", flat=True)

        pending_task_users = Task.objects.filter(
            project_id=pk, 
            annotation_users=user.id, 
            task_status__in=[INCOMPLETE], 
            id__in=annotation_tasks
        ).count()

        # Max tasks that can be assigned to the user based on the project constraint
        tasks_to_be_assigned = project.max_pending_tasks_per_user - pending_task_users

        # Check if user exceeded max_tasks_per_user
        if project.max_tasks_per_user != -1:
            tasks_assigned_to_user = Task.objects.filter(
                project_id=pk, annotation_users=user.id
            ).count()
            
            if tasks_assigned_to_user >= project.max_tasks_per_user:
                return Response(
                    {"message": f"You are only allowed a total of {project.max_tasks_per_user} tasks"},
                    status=status.HTTP_200_OK,
                )

            max_task_that_can_be_assigned = min(
                project.max_tasks_per_user - tasks_assigned_to_user,
                tasks_to_be_assigned,
            )
        else:
            max_task_that_can_be_assigned = tasks_to_be_assigned

        # Fetch all available tasks
        tasks = Task.objects.filter(
            project_id=pk,
            task_status__in=[INCOMPLETE]
        ).exclude(
            annotation_users=user.id 
        ).annotate(
            annotator_count=Count("annotation_users")
        ).filter(
            annotator_count__lt=project.required_annotators_per_task
        ).order_by("id")  

        # unique unassigned data items (as in the new design each annotator is given a seperate task of the same data item)
        data_items_vs_tasks_map = {t.input_data.id: t for t in tasks}
        data_items_of_unassigned_tasks = set(data_items_vs_tasks_map.keys())

        #  Identify assigned data items
        data_items_of_assigned_tasks = set(
            proj_annotations.values_list("task__input_data_id", flat=True)
        )
        proj_annotations_annotated = Annotation_model.objects.filter(
            task__project_id=pk, 
            annotation_status__in=[UNLABELED, SKIPPED, DRAFT, LABELED, TO_BE_REVISED], 
            completed_by=user, 
            annotation_type=1
        )
        data_items_of_assigned_tasks.update(
            proj_annotations_annotated.values_list("task__input_data_id", flat=True)
        )

        # Find unassigned data items that can still be assigned
        all_unassigned_data_items = data_items_of_unassigned_tasks - data_items_of_assigned_tasks
        tasks = [data_items_vs_tasks_map[task_id] for task_id in all_unassigned_data_items]
        assignable_tasks = tasks[:max_task_that_can_be_assigned] if max_task_that_can_be_assigned else tasks[:tasks_to_be_assigned]
        return len(assignable_tasks)





class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project ViewSet
    """

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, pk, *args, **kwargs):
        """
        Retrieves a project given its ID
        """
        project_response = super().retrieve(request, *args, **kwargs)

        datasets = (
            DatasetInstance.objects.only("instance_id", "instance_name")
            .filter(instance_id__in=project_response.data["dataset_id"])
            .values("instance_id", "instance_name")
        )
        project_response.data["datasets"] = datasets
        project_response.data.pop("dataset_id")

        # Add a new field to the project response to indicate project status
        project_response.data["status"] = get_project_creation_status(pk)
        project_response.data["task_creation_status"] = get_task_creation_status(pk)

        # Add a new field to the project to indicate the async project export status and last export date
        (
            project_export_status,
            last_project_export_date,
            last_project_export_time,
        ) = get_project_export_status(pk)
        project_response.data["last_project_export_status"] = project_export_status
        project_response.data["last_project_export_date"] = last_project_export_date
        project_response.data["last_project_export_time"] = last_project_export_time

        # Add the details about the last data pull
        (
            last_pull_status,
            last_pull_date,
            last_project_export_time,
            last_project_export_result,
        ) = get_project_pull_status(pk)
        project_response.data["last_pull_status"] = last_pull_status
        project_response.data["last_pull_date"] = last_pull_date
        project_response.data["last_pull_time"] = last_project_export_time
        project_response.data["last_pull_result"] = last_project_export_result

        # Add a field to specify the no. of available tasks to be assigned
        project_response.data["unassigned_task_count"] = get_task_count_unassigned(
            pk, request.user
        )
        project = Project.objects.get(id=pk)
        try:
            allow_unireview = project.metadata_json["allow_unireview"]
        except:
            allow_unireview = False
        if project.required_annotators_per_task > 1 and allow_unireview:
            similar_task_incomplete = Task.objects.filter(
                project_id=OuterRef("project_id"),
                input_data=OuterRef("input_data"),
                task_status=INCOMPLETE,
            ).exclude(id=OuterRef("id"))

            tasks = (
                Task.objects.filter(
                    project_id=pk, task_status=ANNOTATED, review_user__isnull=True
                )
                .exclude(annotation_users=request.user.id)
                .exclude(Exists(similar_task_incomplete))
                .count()
            )
            project_response.data["labeled_task_count"] = tasks
        else:
            project_response.data["labeled_task_count"] = (
                Task.objects.filter(project_id=pk)
                .filter(task_status=ANNOTATED)
                .filter(review_user__isnull=True)
                .exclude(annotation_users=request.user.id)
                .count()
            )

        # Add a field to specify the no. of reviewed tasks
        project_response.data["reviewed_task_count"] = (
            Task.objects.filter(project_id=pk)
            .filter(task_status=REVIEWED)
            .filter(super_check_user__isnull=True)
            .exclude(annotation_users=request.user.id)
            .exclude(review_user=request.user.id)
            .count()
        )

        return project_response

    def list(self, request, *args, **kwargs):
        """
        List all Projects
        """
        try:
            # projects = self.queryset.filter(annotators=request.user)
            if request.user.is_superuser:
                projects = self.queryset
            elif request.user.role == User.ORGANIZATION_OWNER:
                projects = self.queryset.filter(
                    organization_id=request.user.organization
                )
            elif request.user.role == User.WORKSPACE_MANAGER:
                projects = (
                    self.queryset.filter(
                        workspace_id__in=Workspace.objects.filter(
                            managers=request.user
                        ).values_list("id", flat=True)
                    )
                    | self.queryset.filter(annotators=request.user)
                    | self.queryset.filter(annotation_reviewers=request.user)
                )
            elif request.user.role == User.SUPER_CHECKER:
                projects = (
                    self.queryset.filter(annotators=request.user)
                    | self.queryset.filter(annotation_reviewers=request.user)
                    | self.queryset.filter(review_supercheckers=request.user)
                )
            elif request.user.role == User.REVIEWER:
                projects = self.queryset.filter(
                    annotators=request.user
                ) | self.queryset.filter(annotation_reviewers=request.user)
            elif request.user.role == User.ANNOTATOR:
                projects = self.queryset.filter(annotators=request.user)

            projects = projects.filter(is_published=True).filter(is_archived=False)

            projects = projects.distinct()

            if (
                "sort_type" in request.query_params
                and request.query_params["sort_type"] == "most_recent_worked_projects"
            ):
                annotations = Annotation_model.objects.filter(completed_by=request.user)
                annotations = annotations.order_by("-updated_at")
                project_ids = []
                project_ids_set = set()
                for annotation in annotations:
                    project_id = annotation.task.project_id.id
                    if project_id not in project_ids_set:
                        project_ids.append(project_id)
                        project_ids_set.add(project_id)
                unannotated_projects = projects.exclude(pk__in=project_ids)
                unannotated_projects = unannotated_projects.order_by(
                    F("published_at").desc(nulls_last=True)
                )
                for project in unannotated_projects:
                    project_ids.append(project.id)
                preserved = Case(
                    *[When(pk=pk, then=pos) for pos, pk in enumerate(project_ids)]
                )
                projects = Project.objects.filter(pk__in=project_ids).order_by(
                    preserved
                )
            else:
                projects = projects.order_by(F("published_at").desc(nulls_last=True))

            projects_json = self.serializer_class(projects, many=True)
            return Response(projects_json.data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"message": "Please Login!"}, status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "sort_type",
                openapi.IN_QUERY,
                description=(
                    "A string specifying the type of sort applied to the list.Enter sort_type=most_recent_worked_projects to sort by most recent else default sort by published_at field will be applied."
                ),
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "project_type",
                openapi.IN_QUERY,
                description=("A string that denotes the type of project"),
                type=openapi.TYPE_STRING,
                enum=PROJECT_TYPE_LIST,
                required=False,
            ),
            openapi.Parameter(
                "project_user_type",
                openapi.IN_QUERY,
                description=(
                    "A string that denotes the type of the user in the project"
                ),
                type=openapi.TYPE_STRING,
                enum=["annotator", "reviewer"],
                required=False,
            ),
            openapi.Parameter(
                "archived_projects",
                openapi.IN_QUERY,
                description=(
                    "A flag that denotes whether the project is archived or not"
                ),
                type=openapi.TYPE_BOOLEAN,
                required=False,
            ),
        ],
        responses={
            200: ProjectSerializerOptimized,
            400: "Please Login!",
        },
    )
    @action(
        detail=False,
        methods=["get"],
        url_name="list-optimized",
        url_path="projects_list/optimized",
    )
    def list_optimized(self, request):
        """
        List all projects with some optimizations.
        """
        try:
            projects = self.queryset.filter(annotators=request.user)
            if request.user.is_superuser:
                projects = self.queryset
            elif request.user.role == User.ORGANIZATION_OWNER:
                projects = self.queryset.filter(
                    organization_id=request.user.organization
                )
            elif request.user.role == User.WORKSPACE_MANAGER:
                projects = (
                    self.queryset.filter(
                        workspace_id__in=Workspace.objects.filter(
                            managers=request.user
                        ).values_list("id", flat=True)
                    )
                    | self.queryset.filter(annotators=request.user)
                    | self.queryset.filter(annotation_reviewers=request.user)
                )
            elif request.user.role == User.SUPER_CHECKER:
                projects = (
                    self.queryset.filter(annotators=request.user)
                    | self.queryset.filter(annotation_reviewers=request.user)
                    | self.queryset.filter(review_supercheckers=request.user)
                )
                projects = projects.filter(is_published=True).filter(is_archived=False)
            elif request.user.role == User.REVIEWER:
                projects = self.queryset.filter(
                    annotators=request.user
                ) | self.queryset.filter(annotation_reviewers=request.user)
                projects = projects.filter(is_published=True).filter(is_archived=False)
            elif request.user.role == User.ANNOTATOR:
                projects = self.queryset.filter(annotators=request.user)
                projects = projects.filter(is_published=True).filter(is_archived=False)
            if "guest_view" in request.query_params:
                projects = (
                    self.queryset.filter(
                        workspace_id__in=Workspace.objects.filter(
                            members=request.user
                        ).values_list("id", flat=True)
                    )
                    .filter(is_published=True)
                    .filter(is_archived=False)
                )
            if "guest_workspace_filter" in request.query_params:
                projects = (
                    self.queryset.filter(workspace_id__guest_workspace=True)
                    .filter(
                        workspace_id__in=Workspace.objects.filter(
                            members=request.user
                        ).values_list("id", flat=True)
                    )
                    .filter(is_published=True)
                    .filter(is_archived=False)
                )

            if "project_user_type" in request.query_params:
                project_user_type = request.query_params["project_user_type"]
                if project_user_type == "annotator":
                    projects = projects.filter(annotators=request.user)
                elif project_user_type == "reviewer":
                    projects = projects.filter(annotation_reviewers=request.user)

            if "project_type" in request.query_params:
                project_type = request.query_params["project_type"]
                projects = projects.filter(project_type=project_type)

            if "archived_projects" in request.query_params:
                archived_projects = request.query_params["archived_projects"]
                archived_projects = True if archived_projects == "true" else False
                projects = projects.filter(is_archived=archived_projects)

            projects = projects.distinct()

            if (
                "sort_type" in request.query_params
                and request.query_params["sort_type"] == "most_recent_worked_projects"
            ):
                annotations = Annotation_model.objects.filter(completed_by=request.user)
                annotations = annotations.order_by("-updated_at")
                project_ids = []
                project_ids_set = set()
                for annotation in annotations:
                    project_id = annotation.task.project_id.id
                    if project_id not in project_ids_set:
                        project_ids.append(project_id)
                        project_ids_set.add(project_id)
                unannotated_projects = projects.exclude(pk__in=project_ids)
                unannotated_projects = unannotated_projects.order_by(
                    F("published_at").desc(nulls_last=True)
                )
                for project in unannotated_projects:
                    project_ids.append(project.id)
                preserved = Case(
                    *[When(pk=pk, then=pos) for pos, pk in enumerate(project_ids)]
                )
                projects = Project.objects.filter(pk__in=project_ids).order_by(
                    preserved
                )
            else:
                projects = projects.order_by(F("published_at").desc(nulls_last=True))

            if "guest_view" in request.query_params:
                included_projects = projects.filter(annotators=request.user)
                excluded_projects = projects.exclude(annotators=request.user)
                included_projects_serialized = ProjectSerializerOptimized(
                    included_projects, many=True
                )
                excluded_projects_serialized = ProjectSerializerOptimized(
                    excluded_projects, many=True
                )
                combined_data = {
                    "included_projects": included_projects_serialized.data,
                    "excluded_projects": excluded_projects_serialized.data,
                }
                return Response(combined_data, status=status.HTTP_200_OK)
            projects_json = ProjectSerializerOptimized(projects, many=True)
            return Response(projects_json.data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"message": "Please Login!"}, status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        method="post",
        request_body=UserEmailSerializer,
        responses={
            201: "User removed",
            404: "User does not exist",
            500: "Server error occured",
        },
    )
    @is_project_editor
    @action(detail=True, methods=["post"], url_name="remove")
    # TODO: Refactor code to handle better role access
    def remove_annotator(self, request, pk=None, freeze_user=True):
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            project = Project.objects.filter(pk=pk).first()
            if not project:
                return Response(
                    {"message": "Project does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            required_annotators_per_task = project.required_annotators_per_task
            for user_id in ids:
                user = User.objects.get(pk=user_id)
                if user in project.frozen_users.all():
                    return Response(
                        {"message": "User is already frozen"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                tasks = Task.objects.filter(
                    Q(project_id=project.id) & Q(annotation_users__in=[user])
                ).filter(Q(task_status="incomplete"))
                annotator_annotation = Annotation_model.objects.filter(
                    Q(completed_by=user)
                    & Q(task__in=tasks)
                    & Q(annotation_type=ANNOTATOR_ANNOTATION)
                )
                reviewer_annotation = Annotation_model.objects.filter(
                    parent_annotation__in=annotator_annotation
                )
                superchecker_annotation = Annotation_model.objects.filter(
                    parent_annotation__in=reviewer_annotation
                )
                annotator_annotation = (
                    annotator_annotation.exclude(annotation_status=LABELED)
                    if required_annotators_per_task > 1
                    else annotator_annotation
                )
                superchecker_annotation.delete()
                reviewer_annotation.delete()
                annotator_annotation.delete()
                for task in tasks:
                    task.super_check_user = None
                    task.review_user = None
                    task.annotation_users.remove(user)
                    task.revision_loop_count = {
                        "super_check_count": 0,
                        "review_count": 0,
                    }
                    task.save()
                tasks.update(task_status="incomplete")  # unassign user from tasks
                # project.annotators.remove(user)
                if freeze_user == True:
                    project.frozen_users.add(user)
                project.save()

                # Creating Notification
                title = f"{project.title}:{project.id} Some annotators have been removed from this project"
                notification_type = "remove_member"
                notification_ids = get_userids_from_project_id(
                    project_id=pk,
                    annotators_bool=True,
                    reviewers_bool=True,
                    super_checkers_bool=True,
                    project_manager_bool=True,
                )
                notification_ids.extend(ids)
                notification_ids_set = list(set(notification_ids))
                createNotification(title, notification_type, notification_ids_set, pk)
            return Response(
                {"message": "User removed from project"},
                status=status.HTTP_201_CREATED,
            )

        except User.DoesNotExist:
            return Response(
                {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @is_project_editor
    @action(detail=True, methods=["post"], url_name="remove_reviewer")
    def remove_reviewer(self, request, pk=None, freeze_user=True):
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            project = Project.objects.filter(pk=pk).first()
            if not project:
                return Response(
                    {"message": "Project does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            for user_id in ids:
                user = User.objects.get(pk=user_id)
                # check if the user is already frozen
                if user in project.frozen_users.all():
                    return Response(
                        {"message": "User is already frozen"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                tasks = (
                    Task.objects.filter(project_id=project.id)
                    .filter(review_user=user)
                    .filter(task_status__in=[ANNOTATED])
                )
                reviewer_annotation = Annotation_model.objects.filter(
                    Q(completed_by=user)
                    & Q(task__in=tasks)
                    & Q(annotation_type=REVIEWER_ANNOTATION)
                )
                superchecker_annotation = Annotation_model.objects.filter(
                    parent_annotation__in=reviewer_annotation
                )
                superchecker_annotation.delete()
                for an in reviewer_annotation:
                    if an.annotation_status == TO_BE_REVISED:
                        parent = an.parent_annotation
                        parent.annotation_status = LABELED
                        parent.save(update_fields=["annotation_status"])
                    an.parent_annotation = None
                    an.save()
                    an.delete()

                for task in tasks:
                    task.super_check_user = None
                    task.review_user = None
                    task.revision_loop_count = {
                        "super_check_count": 0,
                        "review_count": 0,
                    }
                    task.task_status = ANNOTATED
                    task.save()
                if freeze_user == True:
                    project.frozen_users.add(user)
                project.save()
                # Creating Notification
                title = f"{project.title}:{project.id} Some annotators have been removed from this project"
                notification_type = "remove_member"
                notification_ids = get_userids_from_project_id(
                    project_id=pk,
                    annotators_bool=True,
                    reviewers_bool=True,
                    super_checkers_bool=True,
                    project_manager_bool=True,
                )
                notification_ids.extend(ids)
                notification_ids_set = list(set(notification_ids))
                createNotification(
                    title, notification_type, notification_ids_set, project.id
                )

            return Response(
                {"message": "User removed from the project"}, status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @is_project_editor
    @action(detail=True, methods=["post"], url_name="remove_superchecker")
    def remove_superchecker(self, request, pk=None, freeze_user=True):
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            project = Project.objects.filter(pk=pk).first()
            if not project:
                return Response(
                    {"message": "Project does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            for user_id in ids:
                user = User.objects.get(pk=user_id)
                # check if the user is already frozen
                if user in project.frozen_users.all():
                    return Response(
                        {"message": "User is already frozen"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                tasks = (
                    Task.objects.filter(project_id=project.id)
                    .filter(super_check_user=user)
                    .filter(task_status__in=[REVIEWED])
                )
                superchecker_annotation = Annotation_model.objects.filter(
                    Q(completed_by=user)
                    & Q(task__in=tasks)
                    & Q(annotation_type=SUPER_CHECKER_ANNOTATION)
                )
                for an in superchecker_annotation:
                    if an.annotation_status == REJECTED:
                        parent = an.parent_annotation
                        grand_parent = parent.parent_annotation
                        parent.annotation_status = ACCEPTED
                        grand_parent.annotation_status = LABELED
                        parent.save(update_fields=["annotation_status"])
                        grand_parent.save(update_fields=["annotation_status"])
                    an.parent_annotation = None
                    an.save()
                    an.delete()

                for task in tasks:
                    task.super_check_user = None
                    rev_loop_count = task.revision_loop_count
                    rev_loop_count["super_check_count"] = 0
                    task.revision_loop_count = rev_loop_count
                    task.task_status = REVIEWED
                    task.save()
                if freeze_user == True:
                    project.frozen_users.add(user)
                project.save()
                # Creating Notification
                title = f"{project.title}:{project.id} Some supercheckers have been removed from this project"
                notification_type = "remove_member"
                notification_ids = get_userids_from_project_id(
                    project_id=pk,
                    annotators_bool=True,
                    reviewers_bool=True,
                    super_checkers_bool=True,
                    project_manager_bool=True,
                )
                notification_ids.extend(ids)
                notification_ids_set = list(set(notification_ids))
                createNotification(title, notification_type, notification_ids_set, pk)

            return Response(
                {"message": "User removed from the project"}, status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"], url_name="remove_frozen_user")
    def remove_frozen_user(self, request, pk=None):
        if "ids" in dict(request.data):
            ids = request.data.get("ids", "")
        else:
            return Response(
                {"message": "key doesnot match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            project = Project.objects.filter(pk=pk).first()
            if not project:
                return Response(
                    {"message": "Project does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            for user_id in ids:
                user = User.objects.get(pk=user_id)
                project.frozen_users.remove(user)
                project.save()
            return Response(
                {"message": "Frozen User removed from the project"},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        method="post",
        manual_parameters=[
            openapi.Parameter(
                "task_status",
                openapi.IN_QUERY,
                description=("A string that denotes the status of task"),
                type=openapi.TYPE_STRING,
                enum=[task_status[0] for task_status in TASK_STATUS],
                required=False,
            ),
            openapi.Parameter(
                "current_task_id",
                openapi.IN_QUERY,
                description=("The unique id identifying the current task"),
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},
        ),
        responses={
            201: TaskSerializer,
            204: "No more tasks available! or No more unlabeled tasks!",
        },
    )
    @action(detail=True, methods=["post"], url_path="next")
    def next(self, request, pk):
        """
        Fetch the next task for the user(annotation or review)
        """
        project = Project.objects.get(pk=pk)
        user_role = request.user.role
        task_status = request.data.get("task_status")
        mode = request.data.get("mode")
        annotation_status = request.data.get("annotation_status")
        current_task_id = request.data.get("current_task_id")

        # Check if the endpoint is being accessed in review mode

        # is_review_mode = (
        #     "mode" in dict(request.query_params)
        #     and request.query_params["mode"] == "review"
        # )
        if mode == "review":
            if project.project_stage == ANNOTATION_STAGE:
                resp_dict = {"message": "Task reviews are not enabled for this project"}
                return Response(resp_dict, status=status.HTTP_403_FORBIDDEN)
        if mode == "supercheck":
            if project.project_stage != SUPERCHECK_STAGE:
                resp_dict = {
                    "message": "Task superchecks are not enabled for this project"
                }
                return Response(resp_dict, status=status.HTTP_403_FORBIDDEN)

        if annotation_status != None:
            if (
                request.user in project.annotation_reviewers.all()
                or request.user in project.annotators.all()
                or request.user in project.review_supercheckers.all()
            ):
                if mode == "review":
                    annotations = Annotation_model.objects.filter(
                        task__project_id=pk,
                        annotation_status=annotation_status,
                        annotation_type=REVIEWER_ANNOTATION,
                        completed_by=request.user.id,
                    )
                elif mode == "annotation":
                    annotations = Annotation_model.objects.filter(
                        task__project_id=pk,
                        annotation_status=annotation_status,
                        annotation_type=ANNOTATOR_ANNOTATION,
                        completed_by=request.user.id,
                    )
                else:
                    annotations = Annotation_model.objects.filter(
                        task__project_id=pk,
                        annotation_status=annotation_status,
                        annotation_type=SUPER_CHECKER_ANNOTATION,
                        completed_by=request.user.id,
                    )
            else:
                if mode == "review":
                    annotations = Annotation_model.objects.filter(
                        task__project_id=pk,
                        annotation_status=annotation_status,
                        annotation_type=REVIEWER_ANNOTATION,
                    )
                elif mode == "annotation":
                    annotations = Annotation_model.objects.filter(
                        task__project_id=pk,
                        annotation_status=annotation_status,
                        annotation_type=ANNOTATOR_ANNOTATION,
                    )
                else:
                    annotations = Annotation_model.objects.filter(
                        task__project_id=pk,
                        annotation_status=annotation_status,
                        annotation_type=SUPER_CHECKER_ANNOTATION,
                    )

            tasks = Task.objects.filter(annotations__in=annotations)
            tasks = tasks.distinct()
            if len(tasks):
                tasks = tasks.filter(
                    **process_search_query(
                        request.GET, "data", list(tasks.first().data.keys())
                    )
                )
            ann_filter1 = annotations.filter(task__in=tasks)
            task_ids = [an.task_id for an in ann_filter1]

            queryset = Task.objects.filter(id__in=task_ids).order_by("id")
            # required_annotators_per_task = project.required_annotators_per_task
            # next_anno = ""
            # if required_annotators_per_task > 1:
            #     try:
            #         curr_anno_id = int(request.data.get("current_annotation_id"))
            #     except Exception as e:
            #         ret_dict = {"message": "Please send the current_annotation_id"}
            #         ret_status = status.HTTP_400_BAD_REQUEST
            #         return Response(ret_dict, status=ret_status)
            #     for task in queryset:
            #         curr_task_anno = ann_filter1.filter(task=task).order_by("id")
            #         ann_ids = [an.id for an in curr_task_anno]
            #         if curr_anno_id != ann_ids[-1]:
            #             for i, c in enumerate(ann_ids):
            #                 if c == curr_anno_id:
            #                     next_anno = ann_ids[i + 1]
            # if next_anno:
            #     queryset = queryset.filter(id=current_task_id)
            # elif current_task_id != None:
            if current_task_id != None:
                queryset = queryset.filter(id__gt=current_task_id)
            for task in queryset:
                # if next_anno:
                #     task_dict = TaskSerializer(task, many=False).data
                #     task_dict["correct_annotation"] = next_anno
                #     return Response(task_dict)
                # elif required_annotators_per_task > 1:
                #     next_anno = ann_filter1.filter(task=task).order_by("id")
                #     task_dict = TaskSerializer(task, many=False).data
                #     task_dict["correct_annotation"] = next_anno[0].id
                #     return Response(task_dict)
                task_dict = TaskSerializer(task, many=False).data
                return Response(task_dict)
            ret_dict = {"message": "No more tasks available!"}
            ret_status = status.HTTP_204_NO_CONTENT
            return Response(ret_dict, status=ret_status)
        # Check if task_status is passed
        if task_status != None:
            if (
                request.user in project.annotation_reviewers.all()
                or request.user in project.annotators.all()
                or request.user in project.review_supercheckers.all()
            ):
                if mode == "review":
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        review_user=request.user.id,
                        task_status=task_status,
                    )
                elif mode == "annotation":
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        annotation_users=request.user.id,
                        task_status=task_status,
                    )
                else:
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        super_check_user=request.user.id,
                        task_status=task_status,
                    )
            else:
                tasks = Task.objects.filter(
                    project_id__exact=project.id,
                    task_status=task_status,
                )

            if len(tasks):
                tasks = tasks.filter(
                    **process_search_query(
                        request.GET, "data", list(tasks.first().data.keys())
                    )
                )

            queryset = tasks.order_by("id")

            if current_task_id != None:
                queryset = queryset.filter(id__gt=current_task_id)
            for task in queryset:
                task_dict = TaskSerializer(task, many=False).data
                return Response(task_dict)
            ret_dict = {"message": "No more tasks available!"}
            ret_status = status.HTTP_204_NO_CONTENT
            return Response(ret_dict, status=ret_status)

        else:
            # Check if there are unattended tasks
            if (
                request.user in project.annotation_reviewers.all()
                or request.user in project.annotators.all()
                or request.user in project.review_supercheckers.all()
            ) and not request.user.is_superuser:
                # Filter Tasks based on whether the request is in review mode or not
                if mode == "review":
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        review_user=request.user.id,
                        task_status=ANNOTATED,
                    )
                elif mode == "annotation":
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        annotation_users=request.user.id,
                        task_status=INCOMPLETE,
                    )
                else:
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        super_check_user=request.user.id,
                        task_status=REVIEWED,
                    )
            else:
                # TODO : Refactor code to reduce DB calls
                # Filter Tasks based on whether the request is in review mode or not
                if mode == "review":
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        task_status=ANNOTATED,
                    )
                elif mode == "annotation":
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        task_status=INCOMPLETE,
                    )
                else:
                    tasks = Task.objects.filter(
                        project_id__exact=project.id,
                        task_status=REVIEWED,
                    )

            if len(tasks):
                tasks = tasks.filter(
                    **process_search_query(
                        request.GET, "data", list(tasks.first().data.keys())
                    )
                )

            unattended_tasks = tasks.order_by("id")

            if current_task_id != None:
                unattended_tasks = unattended_tasks.filter(id__gt=current_task_id)
            for task in unattended_tasks:
                task_dict = TaskSerializer(task, many=False).data
                return Response(task_dict)
            ret_dict = {"message": "No more unlabeled tasks!"}
            ret_status = status.HTTP_204_NO_CONTENT
            return Response(ret_dict, status=ret_status)

    @is_organization_owner_or_workspace_manager
    def create(self, request, *args, **kwargs):
        """
        Creates a project

        Authenticated only for organization owner or workspace manager
        """
        # Read project details from api request
        project_type = request.data.get("project_type")
        filter_string = request.data.get("filter_string")
        sampling_mode = request.data.get("sampling_mode")
        sampling_parameters = request.data.get("sampling_parameters_json")
        variable_parameters = request.data.get("variable_parameters")
        automatic_annotation_creation_mode = request.data.get(
            "automatic_annotation_creation_mode"
        )

        dataset_instance_ids = request.data.get("dataset_id")
        if type(dataset_instance_ids) != list:
            dataset_instance_ids = [dataset_instance_ids]
        if (
            project_type == "MultipleInteractionEvaluation"
            and "metadata_json" in request.data
        ):
            res, mes = validate_metadata_json_format(request.data["metadata_json"])
            if not res:
                ret_dict = {"message": mes}
                ret_status = status.HTTP_400_BAD_REQUEST
                return Response(ret_dict, status=ret_status)
        project_response = super().create(request, *args, **kwargs)
        project_id = project_response.data["id"]

        proj = Project.objects.get(id=project_id)
        if proj.required_annotators_per_task > 1:
            proj.project_stage = REVIEW_STAGE
        proj.save()

        create_parameters_for_task_creation.delay(
            project_type=project_type,
            dataset_instance_ids=dataset_instance_ids,
            filter_string=filter_string,
            sampling_mode=sampling_mode,
            sampling_parameters=sampling_parameters,
            project_id=project_id,
            variable_parameters=variable_parameters,
            automatic_annotation_creation_mode=automatic_annotation_creation_mode,
        )
        return project_response

    @is_project_editor
    @project_is_archived
    def update(self, request, pk=None, *args, **kwargs):
        """
        Update project details
        """
        # creating notifications
        project = Project.objects.get(pk=pk)
        title = f"{project.title}:{project.id} Project has been updated"
        notification_type = "project_update"
        notification_ids = get_userids_from_project_id(
            project_id=pk,
            annotators_bool=True,
            reviewers_bool=True,
            super_checkers_bool=True,
            project_manager_bool=True,
        )
        createNotification(title, notification_type, notification_ids, pk)
        return super().update(request, *args, **kwargs)

    @is_project_editor
    @project_is_archived
    def partial_update(self, request, pk=None, *args, **kwargs):
        return super().partial_update(request, pk, *args, **kwargs)

    @is_project_editor
    @project_is_published
    def destroy(self, request, pk=None, *args, **kwargs):
        """
        Delete a project
        """
        return super().delete(request, *args, **kwargs)

    # TODO : add exceptions
    @action(detail=True, methods=["POST", "GET"], name="Archive Project")
    @is_project_editor
    def archive(self, request, pk=None, *args, **kwargs):
        """
        Archive a published project
        """
        project = Project.objects.get(pk=pk)
        project.is_archived = not project.is_archived
        project.save()
        return super().retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["GET"],
        name="Get Project Annotators",
        url_name="get_project_annotators",
    )
    def get_project_annotators(self, request, pk=None, *args, **kwargs):
        """
        Get the list of annotators in the project
        """
        ret_dict = {}
        ret_status = 0
        try:
            project = Project.objects.get(pk=pk)
            serializer = ProjectUsersSerializer(project, many=False)
            ret_dict = serializer.data
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(
        detail=True,
        methods=["GET"],
        name="Get Tasks of a Project",
        url_name="get_project_tasks",
    )
    @project_is_archived
    def get_project_tasks(self, request, pk=None, *args, **kwargs):
        """
        Get the list of tasks in the project
        """
        ret_dict = {}
        ret_status = 0
        try:
            # role check
            if (
                request.user.role == User.ORGANIZATION_OWNER
                or request.user.role == User.WORKSPACE_MANAGER
                or request.user.is_superuser
            ):
                tasks = Task.objects.filter(project_id=pk).order_by("id")
            elif request.user.role == User.ANNOTATOR:
                tasks = Task.objects.filter(
                    project_id=pk, annotation_users=request.user
                ).order_by("id")
            tasks = tasks.filter(
                **process_search_query(
                    request.GET, "data", list(tasks.first().data.keys())
                )
            )
            serializer = TaskSerializer(tasks, many=True)
            ret_dict = serializer.data
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except AttributeError:
            ret_dict = {"message": "No tasks found!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(
        detail=True,
        methods=["POST"],
        name="Assign new tasks to user",
        url_name="assign_new_tasks",
    )
    @project_is_archived
    def assign_new_tasks(self, request, pk, *args, **kwargs):
        """
        Pull a new batch of unassigned tasks for this project
        and assign to the user
        """
        cur_user = request.user
        project = Project.objects.get(pk=pk)
        if not project.is_published:
            return Response(
                {"message": "This project is not yet published"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProjectUsersSerializer(project, many=False)
        annotators = serializer.data["annotators"]
        annotator_ids = set()
        for annotator in annotators:
            annotator_ids.add(annotator["id"])
        # verify if user belongs in project annotators
        if not cur_user.id in annotator_ids:
            return Response(
                {"message": "You are not assigned to this project"},
                status=status.HTTP_403_FORBIDDEN,
            )
        # check if user has pending tasks
        # the below logic will work only for required_annotators_per_task=1
        # TO-DO Modify and use the commented logic to cover all cases
        proj_annotations = Annotation_model.objects.filter(task__project_id=pk).filter(
            annotation_status__exact=UNLABELED, completed_by=cur_user
        )
        annotation_tasks = [anno.task.id for anno in proj_annotations]
        pending_tasks = (
            Task.objects.filter(project_id=pk)
            .filter(annotation_users=cur_user.id)
            .filter(task_status__in=[INCOMPLETE, UNLABELED])
            .filter(id__in=annotation_tasks)
            .count()
        )
        # assigned_tasks_queryset = Task.objects.filter(project_id=pk).filter(annotation_users=cur_user.id)
        # assigned_tasks = assigned_tasks_queryset.count()
        # completed_tasks = Annotation_model.objects.filter(task__in=assigned_tasks_queryset).filter(completed_by__exact=cur_user.id).count()
        # pending_tasks = assigned_tasks - completed_tasks
        if pending_tasks >= project.max_pending_tasks_per_user:
            return Response(
                {"message": "Your pending task count is too high"},
                status=status.HTTP_403_FORBIDDEN,
            )
        tasks_to_be_assigned = project.max_pending_tasks_per_user - pending_tasks

        if "num_tasks" in dict(request.data):
            task_pull_count = request.data["num_tasks"]
            tasks_to_be_assigned = min(tasks_to_be_assigned, task_pull_count)

        lock_set = False
        while lock_set == False:
            if project.is_locked(ANNOTATION_LOCK):
                sleep(settings.PROJECT_LOCK_RETRY_INTERVAL)
                continue
            else:
                try:
                    project.set_lock(cur_user, ANNOTATION_LOCK)
                    lock_set = True
                except Exception as e:
                    continue
        # check if the project contains eligible tasks to pull
        tasks = Task.objects.filter(project_id=pk)
        if project.required_annotators_per_task > 1:
            similar_task_count = (
                Task.objects
                .filter(
                    project_id=OuterRef('project_id'),
                    input_data=OuterRef('input_data'),
                    task_status=ANNOTATED,
                )
                .exclude(id=OuterRef('id'))
                .values('input_data')
                .annotate(count=Count('id'))
                .values('count')[:1]  # Get the count (or null if none)
            )

            tasks = (
                Task.objects
                .filter(project_id=pk)
                .annotate(similar_annotated_count=Subquery(similar_task_count, output_field=IntegerField()))
                .order_by('-similar_annotated_count')
            )
        else:
            tasks = tasks.order_by("id")
        tasks = (
            tasks.filter(task_status__in=[INCOMPLETE])
            .exclude(annotation_users=cur_user.id)
            .annotate(annotator_count=Count("annotation_users"))
        )
        tasks = tasks.filter(
            annotator_count__lt=project.required_annotators_per_task
        ).distinct()
        if not tasks:
            project.release_lock(ANNOTATION_LOCK)
            return Response(
                {"message": "No tasks left for assignment in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )
        max_task_that_can_be_assigned = 0
        if project.max_tasks_per_user != -1:
            tasks_assigned_to_user = (
                Task.objects.filter(project_id=pk)
                .filter(annotation_users=cur_user.id)
                .count()
            )
            if tasks_assigned_to_user >= project.max_tasks_per_user:
                return Response(
                    {
                        "message": f"You are only allowed a total of {project.max_tasks_per_user} tasks"
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                max_task_that_can_be_assigned = min(
                    project.max_tasks_per_user - tasks_assigned_to_user,
                    tasks_to_be_assigned,
                )
        proj_annotations_annotated = Annotation_model.objects.filter(
            task__project_id=pk
        ).filter(
            annotation_status__in=[UNLABELED, SKIPPED, DRAFT, LABELED, TO_BE_REVISED],
            completed_by=cur_user,
            annotation_type=1,
        )
        (
            data_items_of_unassigned_tasks,
            data_items_of_assigned_tasks,
            data_items_vs_tasks_map,
        ) = (set(), set(), {})
        for t in tasks:
            if not t.annotation_users.all():
                data_items_vs_tasks_map[t.input_data.id] = t
                data_items_of_unassigned_tasks.add(t.input_data.id)
        for anno in proj_annotations:
            data_items_of_assigned_tasks.add(anno.task.input_data.id)
        for anno_ann in proj_annotations_annotated:
            data_items_of_assigned_tasks.add(anno_ann.task.input_data.id)
        all_unassigned_data_items = (
            data_items_of_unassigned_tasks - data_items_of_assigned_tasks
        )
        tasks = [data_items_vs_tasks_map[audt] for audt in all_unassigned_data_items]
        if max_task_that_can_be_assigned:
            tasks = tasks[:max_task_that_can_be_assigned]
        else:
            tasks = tasks[:tasks_to_be_assigned]
        if not tasks:
            project.release_lock(ANNOTATION_LOCK)
            return Response(
                {"message": "No tasks left for assignment in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )
        for task in tasks:
            task.annotation_users.add(cur_user)
            task.save()
            result = []
            annotator_anno_count = Annotation_model.objects.filter(
                task_id=task, annotation_type=ANNOTATOR_ANNOTATION
            ).count()
            if annotator_anno_count == 0:
                cur_user_anno_count = Annotation_model.objects.filter(
                    task_id=task,
                    annotation_type=ANNOTATOR_ANNOTATION,
                    completed_by=cur_user,
                ).count()
                if cur_user_anno_count == 0:
                    base_annotation_obj = Annotation_model(
                        result=result,
                        task=task,
                        completed_by=cur_user,
                    )
                    try:
                        base_annotation_obj.save()
                    except IntegrityError as e:
                        print(
                            f"Task, completed_by and parent_annotation fields are same while assigning new review task "
                            f"for project id-{project.id}, user-{cur_user.email}"
                        )
            else:
                cur_user_anno_count = Annotation_model.objects.filter(
                    task_id=task,
                    annotation_type=ANNOTATOR_ANNOTATION,
                    completed_by=cur_user,
                ).count()
                if cur_user_anno_count == 0:
                    task.annotation_users.remove(cur_user)
                    task.save()
        project.release_lock(ANNOTATION_LOCK)
        return Response(
            {"message": "Tasks assigned successfully"}, status=status.HTTP_200_OK
        )
    @action(
        detail=False,
        methods=["POST"],
        url_path="allocate_tasks",
        name="Allocate tasks to user with role"
    )
    def allocate_tasks_to_user(self, request, *args, **kwargs):
        """
        Assign tasks to a user based on allocation_type:
        1 - Annotator
        2 - Reviewer
        3 - Super Checker (SC)
        """
        project_id = request.data.get("projectID")
        task_ids = request.data.get("taskIDs", [])
        user_id = request.data.get("userID")
        allocation_type = int(request.data.get("allocation_type", 1))  # default to 1

        if not all([project_id, task_ids, user_id, allocation_type]):
            return Response(
                {"message": "Missing one or more required fields: projectID, taskIDs, userID, allocation_type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(pk=project_id)
            user = User.objects.get(pk=user_id)
        except Project.DoesNotExist:
            return Response({"message": "Invalid project ID"}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"message": "Invalid user ID"}, status=status.HTTP_404_NOT_FOUND)

        valid_tasks = Task.objects.filter(id__in=task_ids, project_id=project_id)
        if not valid_tasks.exists():
            return Response({"message": "No valid tasks found for the given IDs and project"}, status=status.HTTP_404_NOT_FOUND)

        result = []
        for task in valid_tasks:
            # Assign user to appropriate field based on allocation_type
            if allocation_type == 1:
                task.annotation_users.add(user)
            elif allocation_type == 2:
                task.review_users.add(user)
            elif allocation_type == 3:
                task.super_check_users.add(user)

            # Check if user already has an annotation of this type on the task
            existing_annotation = Annotation_model.objects.filter(
                task=task,
                annotation_type=allocation_type,
                completed_by=user
            ).exists()

            if not existing_annotation:
                annotation = Annotation_model(
                    result=result,
                    task=task,
                    completed_by=user,
                    annotation_type=allocation_type
                )
                try:
                    annotation.save()
                except IntegrityError:
                    print(f"Annotation already exists for task {task.id}, user {user.email}, type {allocation_type}")

        return Response({"message": "Tasks successfully allocated"}, status=status.HTTP_200_OK)

    @action(
        detail=True, methods=["post"], name="Unassign tasks", url_name="unassign_tasks"
    )
    @project_is_archived
    def unassign_tasks(self, request, pk, *args, **kwargs):
        """
        Unassigns all unlabeled tasks from an annotator.
        """
        user_type = "annotator"
        user, response = get_user_from_query_params(request, user_type, pk)
        if response != None:
            return response

        status_type = "annotation"
        annotation_status = get_status_from_query_params(request, status_type)

        task_ids = None

        flag = "annotation_status" in request.query_params
        if flag == False:
            task_ids, response = get_task_ids(request)
            print(task_ids)
            if response != None:
                return response

        if flag == False and task_ids == None:
            return Response(
                {"message": "Either provide annotation_status or task_ids"},
                status=status.HTTP_404_NOT_FOUND,
            )

        ann, response = get_annotations_for_project(
            flag, pk, user, annotation_status, task_ids, ANNOTATOR_ANNOTATION
        )
        if response != None:
            return response
        if ann != None:
            review_annotations_ids = []
            reviewer_pulled_tasks = []
            for ann1 in ann:
                try:
                    review_annotation_obj = Annotation_model.objects.get(
                        parent_annotation=ann1
                    )
                    review_annotations_ids.append(review_annotation_obj.id)
                    reviewer_pulled_tasks.append(review_annotation_obj.task_id)
                except:
                    pass
            if task_ids == None:
                task_ids = [an.task_id for an in ann]
            print(task_ids)
            review_annotations = Annotation_model.objects.filter(
                id__in=review_annotations_ids
            )

            super_check_annotations_ids = []
            supercheck_pulled_tasks = []
            for ann2 in review_annotations:
                try:
                    super_check_annotation_obj = Annotation_model.objects.get(
                        parent_annotation=ann2
                    )
                    super_check_annotations_ids.append(super_check_annotation_obj.id)
                    supercheck_pulled_tasks.append(super_check_annotation_obj.task_id)
                except:
                    pass

            super_check_annotations = Annotation_model.objects.filter(
                id__in=super_check_annotations_ids
            )
            super_check_annotations.delete()
            super_check_tasks = Task.objects.filter(id__in=supercheck_pulled_tasks)
            if super_check_tasks.count() > 0:
                super_check_tasks.update(super_check_user=None)

            review_annotations.delete()
            reviewed_tasks = Task.objects.filter(id__in=reviewer_pulled_tasks)
            if reviewed_tasks.count() > 0:
                reviewed_tasks.update(review_user=None)

            ann.delete()

            tasks = Task.objects.filter(id__in=task_ids)
            if tasks.count() > 0:
                for task in tasks:
                    task.revision_loop_count = {
                        "super_check_count": 0,
                        "review_count": 0,
                    }
                    # task.unassign(user)
                    task.annotation_users.clear()
                    task.task_status = INCOMPLETE
                    task.save()

                return Response(
                    {"message": "Tasks unassigned"}, status=status.HTTP_200_OK
                )
            return Response(
                {"message": "No tasks to unassign"}, status=status.HTTP_200_OK
            )
        return Response(
            {"message": "Only annotators can unassign tasks"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "from_date": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The start date",
                    format="date",
                ),
                "to_date": openapi.Schema(
                    type=openapi.TYPE_STRING, description="The end date", format="date"
                ),
            },
            required=["from_date", "to_date"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username": openapi.Schema(type=openapi.TYPE_STRING),
                        "mail": openapi.Schema(
                            type=openapi.TYPE_STRING, format="email"
                        ),
                        "total_annoted_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "avg_lead_time": openapi.Schema(
                            type=openapi.TYPE_NUMBER, format="float"
                        ),
                        "total_assigned_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "skipped_tasks": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "total_pending_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                    },
                ),
            ),
            404: "Project does not exist!",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Assign new tasks for review to user",
        url_name="assign_new_review_tasks",
    )
    @project_is_archived
    def assign_new_review_tasks(self, request, pk, *args, **kwargs):
        """
        Pull a new batch of labeled tasks and assign to the reviewer
        """
        try:
            allow_unireview = project.metadata_json["allow_unireview"]
        except:
            allow_unireview = False
        cur_user = request.user
        project = Project.objects.get(pk=pk)
        if not project.is_published:
            return Response(
                {"message": "This project is not yet published"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not (
            project.project_stage == REVIEW_STAGE
            or project.project_stage == SUPERCHECK_STAGE
        ):
            return Response(
                {"message": "Task reviews are disabled for this project"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProjectUsersSerializer(project, many=False)
        annotation_reviewers = serializer.data["annotation_reviewers"]
        reviewer_ids = set()
        for annotation_reviewer in annotation_reviewers:
            reviewer_ids.add(annotation_reviewer["id"])
        # verify if user belongs in annotation_reviewers for this project
        if not cur_user.id in reviewer_ids:
            return Response(
                {"message": "You are not assigned to review this project"},
                status=status.HTTP_403_FORBIDDEN,
            )
        lock_set = False
        while lock_set == False:
            if project.is_locked(REVIEW_LOCK):
                sleep(settings.PROJECT_LOCK_RETRY_INTERVAL)
                continue
            else:
                try:
                    project.set_lock(cur_user, REVIEW_LOCK)
                    lock_set = True
                except Exception as e:
                    continue
        # check if the project contains eligible tasks to pull
        tasks = (
            Task.objects.filter(project_id=pk)
            .filter(task_status=ANNOTATED)
            .filter(review_user__isnull=True)
            .exclude(annotation_users=cur_user.id)
            .distinct()
        )
        if not tasks:
            project.release_lock(REVIEW_LOCK)
            return Response(
                {"message": "No tasks available for review in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )
        task_pull_count = project.tasks_pull_count_per_batch
        if "num_tasks" in dict(request.data):
            task_pull_count = request.data["num_tasks"]

        if project.required_annotators_per_task > 1 and allow_unireview:
            task_ids = (
                Annotation_model.objects
                .filter(task__in=tasks)
                .filter(annotation_type=ANNOTATOR_ANNOTATION)
                .filter(annotation_status="labeled")  # focus only on labeled ones
                .values("task__input_data")  # group by input_data
                .annotate(tasks_with_labeled_count=Count("task", distinct=True))  # count tasks sharing this input_data
                .order_by("-tasks_with_labeled_count")  # order by that count
                .values_list("task", flat=True)  # get task IDs back
            )
        else:
        # Sort by most recently updated annotation; temporary change
            task_ids = (
                Annotation_model.objects.filter(task__in=tasks)
                .filter(annotation_type=ANNOTATOR_ANNOTATION)
                .distinct()
                .order_by("-updated_at")
                .values_list("task", flat=True)
            )
        # tasks = tasks.order_by("id")
        task_ids = list(task_ids)
        task_ids = task_ids[:task_pull_count]
        seen = set()
        required_annotators_per_task = project.required_annotators_per_task
        corrupted_tasks = set()
        print("Before loop: ",task_ids)
        if required_annotators_per_task > 1 and allow_unireview:
            seen_tasks = set(task_ids)
            for i in range(len(task_ids)):
                ti = task_ids[i]
                t = Task.objects.get(id=ti)
                similar_tasks = (
                    Task.objects.filter(input_data=t.input_data, project_id=project.id)
                    .filter(task_status=ANNOTATED)
                    .filter(review_user__isnull=True)
                    .exclude(id=t.id)
                )
                corrupt_tasks = (
                    Task.objects.filter(input_data=t.input_data, project_id=project.id)
                    .filter(task_status=INCOMPLETE)
                    .filter(review_user__isnull=True)
                    .exclude(id=t.id)
                )
                
                if corrupt_tasks:
                    corrupted_tasks.add(task_ids[i])
                    print(f"Corrupt tasks related to {ti} inside loop iteration {i}: ",corrupt_tasks)
                    continue
                for j in range(len(similar_tasks)):
                    st = similar_tasks[j]
                    if st.id not in seen_tasks:
                        task_ids.append(st.id)
                print(f"Task_id inside loop iteration {i}: ",ti)
                
                print(f"Similar tasks inside loop iteration {i}: ",similar_tasks)
        print("Corrupted tasks after loop: ",corrupted_tasks)
        print("Task_ids after loop: ",task_ids)
        task_ids = [t for t in task_ids if t not in corrupted_tasks]
        # task_ids = task_ids[:task_pull_count]
        # if required_annotators_per_task > 1:
        #     task_ids = filter_tasks_for_review_filter_criteria(task_ids)
        if len(task_ids) == 0:
            project.release_lock(REVIEW_LOCK)
            return Response(
                {"message": "No tasks available for review in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )
            
        is_MultipleInteractionEvaluation = (
            project.project_type == "MultipleInteractionEvaluation"
        )
        #print(task_ids)
        for task_id in task_ids:
            if task_id in seen:
                continue
            seen.add(task_id)
            task = Task.objects.get(pk=task_id)
            if is_MultipleInteractionEvaluation:
                add_extra_task_data(task, project)
            task.review_user = cur_user
            task.save()
            rec_ann = (
                Annotation_model.objects.filter(task_id=task_id)
                .filter(annotation_type=ANNOTATOR_ANNOTATION)
                .order_by("updated_at")
            )
            curr_response = {}
            def dict_to_string(d):
                return "{" + ", ".join(f"{key}: {value}" for key, value in d.items()) + "}"
            try:
                for qa in rec_ann[0].result[0]["model_responses_json"]:
                    curr_response[qa["model_name"]] = int(qa["questions_response"][0]["response"][0])
                task.data["current_rating"] = dict_to_string(curr_response)
                if "curr_rating" in task.data:
                    del task.data["curr_rating"]
                task.save()
            except:
                True
            reviewer_anno = Annotation_model.objects.filter(
                task_id=task_id, annotation_type=REVIEWER_ANNOTATION
            )
            reviewer_anno_count = Annotation_model.objects.filter(
                task_id=task_id, annotation_type=REVIEWER_ANNOTATION
            ).count()
            if reviewer_anno_count == 0:
                base_annotation_obj = Annotation_model(
                    result=rec_ann[0].result,
                    task=task,
                    completed_by=cur_user,
                    annotation_status="unreviewed",
                    parent_annotation=rec_ann[0],
                    annotation_type=REVIEWER_ANNOTATION,
                    annotation_notes=rec_ann[0].annotation_notes,
                )
                try:
                    base_annotation_obj.save()
                except IntegrityError as e:
                    print(
                        f"Task, completed_by and parent_annotation fields are same while assigning new review task "
                        f"for project id-{project.id}, user-{cur_user.email}"
                    )
            else:
                task.review_user = reviewer_anno[i].completed_by
                task.save()
        project.release_lock(REVIEW_LOCK)
        return Response(
            {"message": "Tasks assigned successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["post"],
        name="Unassign review tasks",
        url_name="unassign_review_tasks",
    )
    @project_is_archived
    def unassign_review_tasks(self, request, pk, *args, **kwargs):
        """
        Unassigns all labeled tasks from a reviewer.
        """
        user_type = "reviewer"
        user, response = get_user_from_query_params(request, user_type, pk)
        if response != None:
            return response

        status_type = "review"
        review_status = get_status_from_query_params(request, status_type)

        task_ids = None

        flag = "review_status" in request.query_params

        if flag == False:
            task_ids, response = get_task_ids(request)
            if response != None:
                return response

        if flag == False and task_ids == None:
            return Response(
                {"message": "Either provide reviewer_id and review_status or task_ids"},
                status=status.HTTP_404_NOT_FOUND,
            )

        ann, response = get_annotations_for_project(
            flag, pk, user, review_status, task_ids, REVIEWER_ANNOTATION
        )
        if response != None:
            return response

        if ann != None:
            superchecker_annotation_ids = []
            supercheck_pulled_tasks = []
            for ann1 in ann:
                try:
                    supercheck_annotation_obj = Annotation_model.objects.get(
                        parent_annotation=ann1
                    )
                    superchecker_annotation_ids.append(supercheck_annotation_obj.id)
                    supercheck_pulled_tasks.append(supercheck_annotation_obj.task_id)
                except:
                    pass
            if task_ids == None:
                task_ids = [an.task_id for an in ann]
            supercheck_annotations = Annotation_model.objects.filter(
                id__in=superchecker_annotation_ids
            )
            supercheck_tasks = Task.objects.filter(id__in=supercheck_pulled_tasks)

            supercheck_annotations.delete()
            if len(supercheck_tasks) > 0:
                supercheck_tasks.update(super_check_user=None)

            for an in ann:
                if an.annotation_status == TO_BE_REVISED:
                    parent = an.parent_annotation
                    parent.annotation_status = LABELED
                    parent.save(update_fields=["annotation_status"])
                an.parent_annotation = None
                an.save()
                an.delete()

            tasks = Task.objects.filter(id__in=task_ids)
            if tasks.count() > 0:
                tasks.update(review_user=None)
                tasks.update(revision_loop_count=default_revision_loop_count_value())
                tasks.update(task_status=ANNOTATED)
                return Response(
                    {"message": "Tasks unassigned"}, status=status.HTTP_200_OK
                )
            return Response(
                {"message": "No tasks to unassign"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"message": "Only reviewers can unassign tasks"},
            status=status.HTTP_403_FORBIDDEN,
        )

    @action(
        detail=True,
        methods=["POST"],
        name="Assign new tasks for supercheck to user",
        url_name="assign_supercheck_tasks",
    )
    @project_is_archived
    def assign_new_supercheck_tasks(self, request, pk, *args, **kwargs):
        """
        Pull a new batch of reviewed tasks and assign to the superchecker
        """
        cur_user = request.user
        project = Project.objects.get(pk=pk)
        if not project.is_published:
            return Response(
                {"message": "This project is not yet published"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not (project.project_stage == SUPERCHECK_STAGE):
            return Response(
                {"message": "Task superchecks are disabled for this project"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProjectUsersSerializer(project, many=False)
        review_supercheckers = serializer.data["review_supercheckers"]
        superchecker_ids = set()
        for review_superchecker in review_supercheckers:
            superchecker_ids.add(review_superchecker["id"])
        # verify if user belongs in annotation_reviewers for this project
        if not cur_user.id in superchecker_ids:
            return Response(
                {"message": "You are not assigned to supercheck this project"},
                status=status.HTTP_403_FORBIDDEN,
            )
        lock_set = False
        while lock_set == False:
            if project.is_locked(SUPERCHECK_LOCK):
                sleep(settings.PROJECT_LOCK_RETRY_INTERVAL)
                continue
            else:
                try:
                    project.set_lock(cur_user, SUPERCHECK_LOCK)
                    lock_set = True
                except Exception as e:
                    continue
        # check if the project contains eligible tasks to pull
        tasks = (
            Task.objects.filter(project_id=pk)
            .filter(task_status=REVIEWED)
            .filter(super_check_user__isnull=True)
            .exclude(annotation_users=cur_user.id)
            .exclude(review_user=cur_user.id)
            .distinct()
        )
        if not tasks:
            project.release_lock(SUPERCHECK_LOCK)
            return Response(
                {"message": "No tasks available for supercheck in this project"},
                status=status.HTTP_404_NOT_FOUND,
            )
        task_pull_count = project.tasks_pull_count_per_batch
        if "num_tasks" in dict(request.data):
            task_pull_count = request.data["num_tasks"]

        sup_exp_rev_tasks_count = (
            Task.objects.filter(project_id=pk)
            .filter(task_status__in=[REVIEWED, EXPORTED, SUPER_CHECKED])
            .distinct()
            .count()
        )
        sup_exp_tasks_count = (
            Task.objects.filter(project_id=pk)
            .filter(task_status__in=[SUPER_CHECKED, EXPORTED])
            .distinct()
            .count()
        )

        max_super_check_tasks_count = math.ceil(
            (project.k_value) * sup_exp_rev_tasks_count / 100
        )
        if sup_exp_tasks_count >= max_super_check_tasks_count:
            return Response(
                {"message": "Maximum supercheck tasks limit reached!"},
                status=status.HTTP_403_FORBIDDEN,
            )
        task_pull_count = min(
            task_pull_count, max_super_check_tasks_count - sup_exp_tasks_count
        )
        # Sort by most recently updated annotation; temporary change
        task_ids = (
            Annotation_model.objects.filter(task__in=tasks)
            .filter(annotation_type=REVIEWER_ANNOTATION)
            .distinct()
            .order_by("-updated_at")
            .values_list("task", flat=True)
        )
        # tasks = tasks.order_by("id")
        task_ids = list(task_ids)
        task_ids = task_ids[:task_pull_count]
        for task_id in task_ids:
            task = Task.objects.get(pk=task_id)
            task.super_check_user = cur_user
            task.save()
            rec_ann = (
                Annotation_model.objects.filter(task_id=task_id)
                .filter(annotation_type=REVIEWER_ANNOTATION)
                .order_by("-updated_at")
            )
            superchecker_anno = Annotation_model.objects.filter(
                task_id=task_id, annotation_type=SUPER_CHECKER_ANNOTATION
            )
            superchecker_anno_count = Annotation_model.objects.filter(
                task_id=task_id, annotation_type=SUPER_CHECKER_ANNOTATION
            ).count()
            if superchecker_anno_count == 0:
                base_annotation_obj = Annotation_model(
                    result=rec_ann[0].result,
                    task=task,
                    completed_by=cur_user,
                    annotation_status="unvalidated",
                    parent_annotation=rec_ann[0],
                    annotation_type=SUPER_CHECKER_ANNOTATION,
                )
                try:
                    base_annotation_obj.save()
                except IntegrityError as e:
                    print(
                        f"Task, completed_by and parent_annotation fields are same while assigning new review task "
                        f"for project id-{project.id}, user-{cur_user.email}"
                    )
            else:
                task.super_check_user = superchecker_anno[0].completed_by
                task.save()
        project.release_lock(SUPERCHECK_LOCK)
        return Response(
            {"message": "Tasks assigned successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["post"],
        name="Unassign supercheck tasks",
        url_name="unassign_supercheck_tasks",
    )
    @project_is_archived
    def unassign_supercheck_tasks(self, request, pk, *args, **kwargs):
        """
        Unassigns all labeled tasks from a superchecker.
        """
        user_type = "superchecker"
        user, response = get_user_from_query_params(request, user_type, pk)
        if response != None:
            return response

        status_type = "supercheck"
        supercheck_status = get_status_from_query_params(request, status_type)

        task_ids = None

        flag = "supercheck_status" in request.query_params

        if flag == False:
            task_ids, response = get_task_ids(request)
            if response != None:
                return response

        if flag == False and task_ids == None:
            return Response(
                {
                    "message": "Either provide superchecker_id and supercheck_status or task_ids"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        ann, response = get_annotations_for_project(
            flag, pk, user, supercheck_status, task_ids, SUPER_CHECKER_ANNOTATION
        )
        if response != None:
            return response
        if ann != None:
            if task_ids == None:
                task_ids = [an.task_id for an in ann]
            for an in ann:
                if an.annotation_status == REJECTED:
                    parent = an.parent_annotation
                    grand_parent = parent.parent_annotation
                    parent.annotation_status = ACCEPTED
                    grand_parent.annotation_status = LABELED
                    parent.save(update_fields=["annotation_status"])
                    grand_parent.save(update_fields=["annotation_status"])
                an.parent_annotation = None
                an.save()
                an.delete()

            tasks = Task.objects.filter(id__in=task_ids)
            if tasks.count() > 0:
                tasks.update(super_check_user=None)
                for task in tasks:
                    rev_loop_count = task.revision_loop_count
                    rev_loop_count["super_check_count"] = 0
                    task.revision_loop_count = rev_loop_count
                    task.task_status = REVIEWED
                    task.save()
                return Response(
                    {"message": "Tasks unassigned"}, status=status.HTTP_200_OK
                )
            return Response(
                {"message": "No tasks to unassign"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"message": "Only supercheckers can unassign tasks"},
            status=status.HTTP_403_FORBIDDEN,
        )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "from_date": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The start date",
                    format="date",
                ),
                "to_date": openapi.Schema(
                    type=openapi.TYPE_STRING, description="The end date", format="date"
                ),
            },
            required=["from_date", "to_date"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username": openapi.Schema(type=openapi.TYPE_STRING),
                        "mail": openapi.Schema(
                            type=openapi.TYPE_STRING, format="email"
                        ),
                        "total_annoted_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "avg_lead_time": openapi.Schema(
                            type=openapi.TYPE_NUMBER, format="float"
                        ),
                        "total_assigned_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "skipped_tasks": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "total_pending_tasks": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                    },
                ),
            ),
            404: "Project does not exist!",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Get Reports  of a Project",
        url_name="get_analytics",
    )
    def get_analytics(self, request, pk=None, *args, **kwargs):
        """
        Get Reports of a Project
        """
        try:
            proj_obj = Project.objects.get(id=pk)
        except Project.DoesNotExist:
            final_result = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
            return Response(final_result, status=ret_status)
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        from_date = from_date + " 00:00"
        to_date = to_date + " 23:59"
        cond, invalid_message = is_valid_date(from_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )
        cond, invalid_message = is_valid_date(to_date)
        if not cond:
            return Response(
                {"message": invalid_message}, status=status.HTTP_400_BAD_REQUEST
            )
        start_date = datetime.strptime(from_date, "%Y-%m-%d %H:%M")
        end_date = datetime.strptime(to_date, "%Y-%m-%d %H:%M")

        if start_date > end_date:
            return Response(
                {"message": "'To' Date should be after 'From' Date"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project_type = proj_obj.project_type
        project_type_lower = project_type.lower()
        is_translation_project = True if "translation" in project_type_lower else False

        users_id = request.user.id

        reports_type = request.data.get("reports_type")

        if reports_type == "review_reports":
            if proj_obj.project_stage > ANNOTATION_STAGE:
                reviewer_names_list = proj_obj.annotation_reviewers.all()
                reviewer_ids = [name.id for name in reviewer_names_list]
                final_reports = []
                if (
                    request.user.role == User.ORGANIZATION_OWNER
                    or request.user.role == User.WORKSPACE_MANAGER
                    or request.user.is_superuser
                ):
                    for id in reviewer_ids:
                        result = get_review_reports(pk, id, start_date, end_date)
                        final_reports.append(result)
                elif users_id in reviewer_ids:
                    result = get_review_reports(pk, users_id, start_date, end_date)
                    final_reports.append(result)
                else:
                    final_reports = {
                        "message": "You do not have enough permissions to access this view!"
                    }
                return Response(final_reports)
            else:
                result = {"message": "disabled task reviews for this project "}
                return Response(result)
        elif reports_type == "superchecker_reports":
            if proj_obj.project_stage > REVIEW_STAGE:
                superchecker_names_list = proj_obj.review_supercheckers.all()
                superchecker_ids = [name.id for name in superchecker_names_list]
                final_reports = []
                if (
                    request.user.role == User.ORGANIZATION_OWNER
                    or request.user.role == User.WORKSPACE_MANAGER
                    or request.user.is_superuser
                ):
                    for id in superchecker_ids:
                        result = get_supercheck_reports(pk, id, start_date, end_date)
                        final_reports.append(result)
                elif users_id in superchecker_ids:
                    result = get_supercheck_reports(pk, users_id, start_date, end_date)
                    final_reports.append(result)
                else:
                    final_reports = {
                        "message": "You do not have enough permissions to access this view!"
                    }
                return Response(final_reports)
            else:
                result = {"message": "disabled task supercheck for this project "}
                return Response(result)

        managers = [
            user1.get_username() for user1 in proj_obj.workspace_id.managers.all()
        ]

        final_result = []
        users_ids = []
        user_mails = []
        user_names = []
        if (
            request.user.role == User.ORGANIZATION_OWNER
            or request.user.role == User.WORKSPACE_MANAGER
            or request.user.is_superuser
        ):
            users_ids = [obj.id for obj in proj_obj.annotators.all()]
            user_mails = [
                annotator.get_username() for annotator in proj_obj.annotators.all()
            ]
            user_names = [annotator.username for annotator in proj_obj.annotators.all()]
        elif (
            (request.user.role == User.ANNOTATOR)
            or (request.user.role == User.REVIEWER)
            or (request.user.role == User.SUPER_CHECKER)
        ):
            users_ids = [request.user.id]
            user_names = [request.user.username]
            user_mails = [request.user.email]
        for index, each_annotator in enumerate(users_ids):
            user_name = user_names[index]
            if (User.objects.get(id=each_annotator)) in (proj_obj.frozen_users.all()):
                user_name = user_name + "*"

            usermail = user_mails[index]
            items = []

            items.append(("Annotator", user_name))
            items.append(("Email", usermail))

            # get total tasks
            all_tasks_in_project = Task.objects.filter(
                Q(project_id=pk) & Q(annotation_users=each_annotator)
            )
            assigned_tasks = all_tasks_in_project.count()
            items.append(("Assigned", assigned_tasks))

            # get labeled task count
            labeled_annotations = Annotation_model.objects.filter(
                task__project_id=pk,
                annotation_status="labeled",
                annotation_type=ANNOTATOR_ANNOTATION,
                updated_at__range=[start_date, end_date],
                completed_by=each_annotator,
            )
            labeled_annotation_ids = [ann.id for ann in labeled_annotations]

            reviewed_ann = Annotation_model.objects.filter(
                parent_annotation_id__in=labeled_annotation_ids,
                annotation_status__in=[
                    ACCEPTED,
                    ACCEPTED_WITH_MAJOR_CHANGES,
                    ACCEPTED_WITH_MINOR_CHANGES,
                ],
            ).count()

            labeled_only_annotations = len(labeled_annotations) - reviewed_ann

            proj = Project.objects.get(id=pk)
            if proj.project_stage > ANNOTATION_STAGE:
                items.append(("Labeled", labeled_only_annotations))
                # get accepted tasks
                annotations_of_reviewer_accepted = Annotation_model.objects.filter(
                    task__project_id=pk,
                    annotation_status="accepted",
                    annotation_type=REVIEWER_ANNOTATION,
                    parent_annotation__updated_at__range=[start_date, end_date],
                )
                parent_anno_ids = [
                    ann.parent_annotation_id for ann in annotations_of_reviewer_accepted
                ]
                annotated_accept_tasks = Annotation_model.objects.filter(
                    id__in=parent_anno_ids,
                    completed_by=each_annotator,
                )

                items.append(("Accepted", annotated_accept_tasks.count()))

                # get accepted with Minor changes tasks count
                annotations_of_reviewer_minor = Annotation_model.objects.filter(
                    task__project_id=pk,
                    annotation_status="accepted_with_minor_changes",
                    annotation_type=REVIEWER_ANNOTATION,
                    parent_annotation__updated_at__range=[start_date, end_date],
                )
                parent_anno_ids_of_minor = [
                    ann.parent_annotation_id for ann in annotations_of_reviewer_minor
                ]
                annotated_accept_minor_changes_tasks = Annotation_model.objects.filter(
                    id__in=parent_anno_ids_of_minor,
                    completed_by=each_annotator,
                )

                items.append(
                    (
                        "Accepted With Minor Changes",
                        annotated_accept_minor_changes_tasks.count(),
                    )
                )

                # get accepted with Major changes tasks count
                annotations_of_reviewer_major = Annotation_model.objects.filter(
                    task__project_id=pk,
                    annotation_status="accepted_with_major_changes",
                    annotation_type=REVIEWER_ANNOTATION,
                    parent_annotation__updated_at__range=[start_date, end_date],
                )
                parent_anno_ids_of_major = [
                    ann.parent_annotation_id for ann in annotations_of_reviewer_major
                ]
                annotated_accept_major_changes_tasks = Annotation_model.objects.filter(
                    id__in=parent_anno_ids_of_major,
                    completed_by=each_annotator,
                )

                items.append(
                    (
                        "Accepted With Major Changes",
                        annotated_accept_major_changes_tasks.count(),
                    )
                )
                # get to_be_revised count
                annotations_of_reviewer_to_be_revised = Annotation_model.objects.filter(
                    task__project_id=pk,
                    annotation_status="to_be_revised",
                    annotation_type=REVIEWER_ANNOTATION,
                    parent_annotation__updated_at__range=[start_date, end_date],
                )
                parent_anno_ids_of_to_be_revised = [
                    ann.parent_annotation_id
                    for ann in annotations_of_reviewer_to_be_revised
                ]
                annotated_to_be_revised_tasks = Annotation_model.objects.filter(
                    id__in=parent_anno_ids_of_to_be_revised,
                    completed_by=each_annotator,
                )
                items.append(("To Be Revised", annotated_to_be_revised_tasks.count()))
            else:
                items.append(("Labeled", len(labeled_annotations)))
            # get unlabeled count
            total_unlabeled_tasks_count = Annotation_model.objects.filter(
                task__project_id=pk,
                annotation_status="unlabeled",
                annotation_type=ANNOTATOR_ANNOTATION,
                updated_at__range=[start_date, end_date],
                completed_by=each_annotator,
            ).count()
            items.append(("Unlabeled", total_unlabeled_tasks_count))

            # get skipped tasks count
            total_skipped_tasks_count = Annotation_model.objects.filter(
                task__project_id=pk,
                annotation_status="skipped",
                annotation_type=ANNOTATOR_ANNOTATION,
                updated_at__range=[start_date, end_date],
                completed_by=each_annotator,
            ).count()

            items.append(("Skipped", total_skipped_tasks_count))

            # get draft tasks count
            total_draft_tasks_count = Annotation_model.objects.filter(
                task__project_id=pk,
                annotation_status="draft",
                annotation_type=ANNOTATOR_ANNOTATION,
                updated_at__range=[start_date, end_date],
                completed_by=each_annotator,
            ).count()

            items.append(("Draft", total_draft_tasks_count))

            total_reviewed_annos = Annotation_model.objects.filter(
                task__project_id=pk,
                task__task_status="reviewed",
                annotation_type=REVIEWER_ANNOTATION,
                updated_at__range=[start_date, end_date],
                parent_annotation__in=labeled_annotation_ids,
            )

            if (
                is_translation_project
                or project_type == "SemanticTextualSimilarity_Scale5"
            ):
                total_word_count_list = []
                for each_task in labeled_annotations:
                    try:
                        total_word_count_list.append(each_task.task.data["word_count"])
                    except:
                        pass

                total_word_count = sum(total_word_count_list)
                items.append(("Word Count", total_word_count))

            elif "OCRTranscription" in project_type:
                total_word_count = 0
                for each_anno in labeled_annotations:
                    total_word_count += ocr_word_count(each_anno.result)
                items.append(("Word Count", total_word_count))

            elif project_type in get_audio_project_types():
                total_duration_list = []
                total_audio_segments_list = []
                total_word_error_rate_ar_list = []
                total_raw_audio_duration_list = []
                for each_task in labeled_annotations:
                    try:
                        total_duration_list.append(
                            get_audio_transcription_duration(each_task.result)
                        )
                        total_audio_segments_list.append(
                            get_audio_segments_count(each_task.result)
                        )
                        total_raw_audio_duration_list.append(
                            each_task.task.data["audio_duration"]
                        )
                    except:
                        pass
                total_duration = sum(total_duration_list)
                total_raw_audio_duration = convert_seconds_to_hours(
                    sum(total_raw_audio_duration_list)
                )
                total_time = convert_seconds_to_hours(total_duration)
                items.append(("Total Segments Duration", total_time))
                items.append(("Total Raw Audio Duration", total_raw_audio_duration))
                total_audio_segments = sum(total_audio_segments_list)
                try:
                    avg_segment_duration = total_duration / total_audio_segments
                    avg_segments_per_task = total_audio_segments / len(
                        labeled_annotations
                    )
                except:
                    avg_segment_duration = 0
                    avg_segments_per_task = 0
                items.append(("Avg Segment Duration", round(avg_segment_duration, 2)))
                items.append(
                    ("Average Segments Per Task", round(avg_segments_per_task, 2))
                )
                for anno in total_reviewed_annos:
                    try:
                        total_word_error_rate_ar_list.append(
                            calculate_word_error_rate_between_two_llm_prompts(
                                anno.result, anno.parent_annotation.result
                            )
                        )
                    except:
                        pass
                if len(total_word_error_rate_ar_list) > 0:
                    avg_word_error_rate_ar = sum(total_word_error_rate_ar_list) / len(
                        total_word_error_rate_ar_list
                    )
                else:
                    avg_word_error_rate_ar = 0
                items.append(
                    ("Average Word Error Rate A/R", round(avg_word_error_rate_ar, 2))
                )

            lead_time_annotated_tasks = [
                annot.lead_time for annot in labeled_annotations
            ]

            avg_lead_time = 0
            if len(lead_time_annotated_tasks) > 0:
                avg_lead_time = sum(lead_time_annotated_tasks) / len(
                    lead_time_annotated_tasks
                )
            items.append(
                ("Average Annotation Time (In Seconds)", round(avg_lead_time, 2))
            )

            final_result.append(dict(items))
        ret_status = status.HTTP_200_OK
        return Response(final_result, status=ret_status)

    @is_organization_owner_or_workspace_manager
    @action(
        detail=True,
        methods=["GET"],
        name="Get Project tasks and annotations and reviewers text",
        url_name="export_project_tasks",
    )
    def export_project_tasks(self, request, pk=None):
        supportred_types = ["CSV", "TSV", "JSON", "csv", "tsv", "json"]
        if "export_type" in dict(request.query_params):
            export_type = request.query_params["export_type"]
            if export_type not in supportred_types:
                final_result = {
                    "message": "exported type only supported formats are : {csv,tsv,json} "
                }
                ret_status = status.HTTP_404_NOT_FOUND
                return Response(final_result, status=ret_status)
        else:
            # default
            export_type = "csv"
        try:
            proj_obj = Project.objects.get(id=pk)
        except Project.DoesNotExist:
            final_result = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
            return Response(final_result, status=ret_status)

        tas = Task.objects.filter(project_id=pk)
        tas_id = [ts.id for ts in tas]
        tas_intext = [ts.data["input_text"] for ts in tas]

        annotation_text_final = []
        reviewer_text_final = []
        annotation_users_final = []
        review_users_final = []
        for id in tas_id:
            ann = Annotation_model.objects.filter(
                task_id=id, parent_annotation__isnull=True
            )
            annotation_text = []
            reviewer_text = []
            annotator_user = []
            reviewer_user = []

            for an in ann:
                user_details = {}
                try:
                    text_json = an.result[0]["value"]
                    text_json["completed_by"] = an.completed_by.id
                    text_json["email"] = an.completed_by.email
                    text_json["first_name"] = an.completed_by.first_name
                except:
                    text_json = {}
                annotation_text.append(text_json)

                user_details["id"] = an.completed_by.id
                user_details["mail"] = an.completed_by.email
                user_details["first_name"] = an.completed_by.first_name
                annotator_user.append(user_details)

            rew = Annotation_model.objects.filter(
                task_id=id, parent_annotation__isnull=False
            )

            for an in rew:
                user_details = {}
                try:
                    text_json = an.result[0]["value"]
                    text_json["completed_by"] = an.completed_by.id
                    text_json["email"] = an.completed_by.email
                    text_json["first_name"] = an.completed_by.first_name
                except:
                    text_json = {}
                reviewer_text.append(text_json)

                user_details["id"] = an.completed_by.id
                user_details["mail"] = an.completed_by.email
                user_details["first_name"] = an.completed_by.first_name
                reviewer_user.append(user_details)

            annotation_text_final.append(annotation_text)
            reviewer_text_final.append(reviewer_text)
            annotation_users_final.append(annotator_user)
            review_users_final.append(reviewer_user)

        zipped = list(
            zip(
                tas_id,
                tas_intext,
                annotation_text_final,
                reviewer_text_final,
                annotation_users_final,
                review_users_final,
            )
        )
        df = pd.DataFrame(zipped)
        df.columns = [
            "task_id",
            "input_text",
            "annotators_text",
            "reviewers_text",
            "annotation_users_final",
            "review_users_final",
        ]

        if export_type == "csv" or export_type == "CSV":
            content = df.to_csv(index=False)
            content_type = "application/.csv"
            filename = "project_details.csv"
        elif export_type == "tsv" or export_type == "TSV":
            content = df.to_csv(sep="\t", index=False)
            content_type = "application/.tsv"
            filename = "project_details.tsv"
        elif export_type == "json" or export_type == "JSON":
            content = df.to_json(force_ascii=False, indent=4)
            content_type = "application/json"
            filename = "project_details.json"

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = 'attachment; filename="%s"' % filename
        response["filename"] = filename
        return response

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "emails": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER, format="ids"),
                    description="List of ids of annotators to be added to project",
                )
            },
            required=["ids"],
        ),
        responses={
            200: "Users added",
            404: "Project does not exist or User does not exist",
            500: "Internal server error",
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        name="Add Project Annotators",
        url_name="add_project_annotators",
    )
    @project_is_archived
    @is_project_editor
    def add_project_annotators(self, request, pk=None, *args, **kwargs):
        """
        Add annotators to the project
        """

        try:
            project = Project.objects.get(pk=pk)
            if "ids" in dict(request.data):
                ids = request.data.get("ids", "")
            else:
                return Response(
                    {"message": "key doesnot match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # check the all the ids in the list are valid or not if valid then add them to the project
            annotators = User.objects.filter(id__in=ids)
            if not annotators:
                return Response(
                    {"message": "annotator does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            for annotator in annotators:
                # check if annotator is already added to project
                if annotator in project.annotators.all():
                    return Response(
                        {"message": "Annotator already added to project"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                project.annotators.add(annotator)
                project.save()

                # Creating Notification
                title = f"{project.title}:{project.id} New annotators have been added to the project"
                notification_type = "add_member"
                notification_ids = get_userids_from_project_id(
                    project_id=pk,
                    annotators_bool=True,
                    reviewers_bool=True,
                    super_checkers_bool=True,
                    project_manager_bool=True,
                )

                createNotification(title, notification_type, notification_ids, pk)

            return Response(
                {"message": "Annotator added to the project"}, status=status.HTTP_200_OK
            )
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(
        detail=True,
        methods=["POST"],
        name="Add Project Reviewers",
        url_name="add_project_reviewers",
    )
    @project_is_archived
    @is_project_editor
    def add_project_reviewers(self, request, pk, *args, **kwargs):
        """
        Adds annotation reviewers to the project
        """
        try:
            project = Project.objects.get(pk=pk)
            if "ids" in dict(request.data):
                ids = request.data.get("ids", "")
            else:
                return Response(
                    {"message": "key doesnot match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            users = User.objects.filter(id__in=ids)
            if not users:
                return Response(
                    {"message": "user does not exist"}, status=status.HTTP_404_NOT_FOUND
                )
            for user in users:
                if user.role == User.ANNOTATOR:
                    return Response(
                        {
                            "message": "One or more users does not have permission to review annotations"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                # check if user is already added to project
                if user in project.annotation_reviewers.all():
                    return Response(
                        {"message": "User already added to project"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                project.annotation_reviewers.add(user)
                project.save()
                # Creating Notification
                title = f"{project.title}:{project.id} New reviewers have been added to project"
                notification_type = "add_member"
                notification_ids = get_userids_from_project_id(
                    project_id=pk,
                    annotators_bool=True,
                    reviewers_bool=True,
                    super_checkers_bool=True,
                    project_manager_bool=True,
                )

                createNotification(title, notification_type, notification_ids, pk)

            return Response({"message": "Reviewers added"}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(
        detail=True,
        methods=["POST"],
        name="Add Project SuperCheckers",
        url_name="add_project_supercheckers",
    )
    @project_is_archived
    @is_project_editor
    def add_project_supercheckers(self, request, pk, *args, **kwargs):
        """
        Adds annotation reviewers to the project
        """
        try:
            project = Project.objects.get(pk=pk)
            if "ids" in dict(request.data):
                ids = request.data.get("ids", "")
            else:
                return Response(
                    {"message": "key doesnot match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            users = User.objects.filter(id__in=ids)
            if not users:
                return Response(
                    {"message": "user does not exist"}, status=status.HTTP_404_NOT_FOUND
                )
            for user in users:
                if user.role == User.ANNOTATOR or user.role == User.REVIEWER:
                    return Response(
                        {
                            "message": "One or more users does not have permission to supercheck review annotations"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                # check if user is already added to project
                if user in project.review_supercheckers.all():
                    return Response(
                        {"message": "User already added to project"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                project.review_supercheckers.add(user)
                project.save()
                # Creating Notification
                title = f"{project.title}:{project.id} New super checkers have been added to project"
                notification_type = "add_member"
                notification_ids = get_userids_from_project_id(
                    project_id=pk,
                    annotators_bool=True,
                    reviewers_bool=True,
                    super_checkers_bool=True,
                    project_manager_bool=True,
                )
                createNotification(title, notification_type, notification_ids, pk)

            return Response(
                {"message": "SuperCheckers added"}, status=status.HTTP_200_OK
            )
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(
        detail=True,
        methods=["POST"],
        name="change project stage",
        url_name="change_project_stage",
    )
    @project_is_archived
    @is_project_editor
    def change_project_stage(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
            new_project_stage = request.data.get("project_stage")
            if new_project_stage == ANNOTATION_STAGE:
                if project.required_annotators_per_task > 1:
                    return Response(
                        {
                            "message": "you can't move to annotation stage for this project because required_annotators_per_task in this project is more than 1 "
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if project.project_stage == ANNOTATION_STAGE:
                    return Response(
                        {"message": "Project is already in Annotation stage"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                elif project.project_stage == SUPERCHECK_STAGE:
                    return Response(
                        {
                            "message": "Project can't directly move from supercheker stage to annotation stage"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                else:
                    project.project_stage = ANNOTATION_STAGE
                    project.save()
                    tasks = Task.objects.filter(project_id=project.id)
                    # get all review tasks
                    reviewed_tasks = tasks.filter(task_status__in=[REVIEWED])
                    ann_rew_exp_tasks = tasks.filter(
                        task_status__in=[REVIEWED, ANNOTATED, EXPORTED]
                    )
                    # change all reviewed task status from "reviewed" to "annotate"
                    reviewed_tasks.update(task_status=ANNOTATED)
                    tasks.update(review_user=None)
                    for tas in ann_rew_exp_tasks:
                        anns = Annotation_model.objects.filter(
                            task_id=tas.id, annotation_type=ANNOTATOR_ANNOTATION
                        )
                        if len(anns) > 0:
                            tas.correct_annotation = anns[0]
                        tas.save()
                    return Response(
                        {"message": "Task moved to Annotation stage from Review stage"},
                        status=status.HTTP_200_OK,
                    )
            elif new_project_stage == REVIEW_STAGE:
                if project.project_stage == REVIEW_STAGE:
                    return Response(
                        {"message": "Project already in Review Stage"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                elif project.project_stage == ANNOTATION_STAGE:
                    tasks = Task.objects.filter(project_id=project.id).filter(
                        task_status__in=[ANNOTATED, EXPORTED]
                    )

                    for tas in tasks:
                        anns = Annotation_model.objects.filter(
                            task_id=tas.id, annotation_type=REVIEWER_ANNOTATION
                        )
                        if len(anns) > 0:
                            rew_status = anns[0].annotation_status
                            if rew_status in [
                                ACCEPTED,
                                ACCEPTED_WITH_MINOR_CHANGES,
                                ACCEPTED_WITH_MAJOR_CHANGES,
                            ]:
                                tas.correct_annotation = anns[0]
                            tas.review_user = anns[0].completed_by
                            if tas.task_status == ANNOTATED and rew_status in [
                                ACCEPTED,
                                ACCEPTED_WITH_MINOR_CHANGES,
                                ACCEPTED_WITH_MAJOR_CHANGES,
                            ]:
                                tas.task_status = REVIEWED
                        else:
                            if tas.task_status == EXPORTED:
                                tas.task_status = ANNOTATED
                            tas.correct_annotation = None
                        tas.save()

                    # tasks.update(task_status=ANNOTATED)
                    project.project_stage = REVIEW_STAGE
                    project.save()
                    return Response(
                        {
                            "message": "Project moved to Review stage from Annotation stage"
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    project.project_stage = REVIEW_STAGE
                    project.save()
                    # (REVIEWED,EXPORTED,SUPERCHECKED)
                    # (SUPERCHECKED->REVIEWED)
                    tasks = Task.objects.filter(project_id=project.id)
                    super_checked_tasks = tasks.filter(task_status__in=[SUPER_CHECKED])
                    rev_exp_sup_tasks = tasks.filter(
                        task_status__in=[REVIEWED, EXPORTED, SUPER_CHECKED]
                    )
                    super_checked_tasks.update(task_status=REVIEWED)
                    tasks.update(super_check_user=None)
                    for tas in rev_exp_sup_tasks:
                        anns = Annotation_model.objects.filter(
                            task_id=tas.id, annotation_type=REVIEWER_ANNOTATION
                        )
                        if len(anns) > 0:
                            tas.correct_annotation = anns[0]
                        tas.save()
                    return Response(
                        {
                            "message": "Project moved to Review stage from SuperCheck stage"
                        },
                        status=status.HTTP_200_OK,
                    )
            elif new_project_stage == SUPERCHECK_STAGE:
                # (REVIEWED,EXPORTED)
                # (EXPORTED->REVIEWED)
                # (REVIEWED->SUPERCHECKED)
                # TO BE DONE
                if project.project_stage == SUPERCHECK_STAGE:
                    return Response(
                        {"message": "Project is already in SuperCheck stage"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                elif project.project_stage == ANNOTATION_STAGE:
                    return Response(
                        {
                            "message": "Project can't directly move from annotation stage to superchecker stage"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                else:
                    tasks = Task.objects.filter(project_id=project.id).filter(
                        task_status__in=[REVIEWED, EXPORTED]
                    )

                    for tas in tasks:
                        anns = Annotation_model.objects.filter(
                            task_id=tas.id, annotation_type=SUPER_CHECKER_ANNOTATION
                        )
                        if len(anns) > 0:
                            supercheck_status = anns[0].annotation_status
                            if supercheck_status in [
                                VALIDATED,
                                VALIDATED_WITH_CHANGES,
                            ]:
                                tas.correct_annotation = anns[0]
                            tas.super_check_user = anns[0].completed_by
                            if tas.task_status == REVIEWED and supercheck_status in [
                                VALIDATED,
                                VALIDATED_WITH_CHANGES,
                            ]:
                                tas.task_status = SUPER_CHECKED
                        else:
                            if tas.task_status == EXPORTED:
                                tas.task_status = REVIEWED
                            tas.correct_annotation = None
                        tas.save()

                    # tasks.update(task_status=ANNOTATED)
                    project.project_stage = SUPERCHECK_STAGE
                    project.save()
                    return Response(
                        {
                            "message": "Project moved to SuperCheck stage from Review stage"
                        },
                        status=status.HTTP_200_OK,
                    )
            else:
                return Response(
                    {"message": "Not a Valid Project Stage!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Project.DoesNotExist:
            return Response(
                {"message": "Project does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "project_type",
                openapi.IN_QUERY,
                description=("A string to pass the project tpye"),
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={200: "Return types of project and its details"},
    )
    @action(detail=False, methods=["GET"], name="Get Project Types", url_name="types")
    def types(self, request, *args, **kwargs):
        """
        Fetches project types
        """
        # project_registry = ProjectRegistry()
        try:
            if "project_type" in dict(request.query_params):
                return Response(
                    ProjectRegistry.get_instance().project_types[
                        request.query_params["project_type"]
                    ],
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    ProjectRegistry.get_instance().data, status=status.HTTP_200_OK
                )
        except Exception:
            print(Exception.args)
            return Response(
                {"message": "Error Occured"}, status=status.HTTP_400_BAD_REQUEST
            )

    def get_task_queryset(self, queryset):
        return queryset

    @action(detail=True, methods=["POST", "GET"], name="Pull new items")
    @project_is_archived
    @is_project_editor
    def pull_new_items(self, request, pk=None, *args, **kwargs):
        """
        Pull New Data Items to the Project
        """
        try:
            project = Project.objects.get(pk=pk)
            if project.sampling_mode != BATCH and project.sampling_mode != FULL:
                ret_dict = {"message": "Sampling Mode is neither FULL nor BATCH!"}
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)
            # Get serializer with the project user data
            try:
                serializer = ProjectUsersSerializer(project, many=False)
            except User.DoesNotExist:
                ret_dict = {"message": "User does not exist!"}
                ret_status = status.HTTP_404_NOT_FOUND
                return Response(ret_dict, status=ret_status)
            # Get project instance and check how many items to pull
            project_type = project.project_type
            ids_to_exclude = Task.objects.filter(project_id__exact=project)
            items = filter_data_items(
                project_type,
                list(project.dataset_id.all()),
                project.filter_string,
            )
            if items:
                if project.sampling_mode == BATCH:
                    try:
                        batch_size = project.sampling_parameters_json["batch_size"]
                        batch_number = project.sampling_parameters_json["batch_number"]
                    except Exception as e:
                        raise Exception("Sampling parameters are not present")
                    if not isinstance(batch_number, list):
                        batch_number = [batch_number]
                    sampled_items = []
                    for batch_num in batch_number:
                        sampled_items += items[
                            batch_size * (batch_num - 1) : batch_size * batch_num
                        ]
                else:
                    sampled_items = items
                ids_to_exclude_set = set(
                    id["input_data"] for id in ids_to_exclude.values("input_data")
                )
                filtered_items = [
                    item
                    for item in sampled_items
                    if item["id"] not in ids_to_exclude_set
                ]
                if not filtered_items:
                    ret_dict = {"message": "No items to pull into the dataset."}
                    ret_status = status.HTTP_404_NOT_FOUND
                    return Response(ret_dict, status=ret_status)
            else:
                ret_dict = {"message": "No items to pull into the dataset."}
                ret_status = status.HTTP_404_NOT_FOUND
                return Response(ret_dict, status=ret_status)
                # Pull new data items in to the project asynchronously
            add_new_data_items_into_project.delay(project_id=pk, items=filtered_items)
            ret_dict = {"message": "Adding new tasks to the project."}
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(detail=True, methods=["POST", "GET"], name="Download a Project")
    @is_project_editor
    def download(self, request, pk=None, *args, **kwargs):
        """
        Download a project
        """
        try:
            project = Project.objects.get(pk=pk)
            project_type = dict(PROJECT_TYPE_CHOICES)[project.project_type]

            include_input_data_metadata_json = request.query_params.get(
                "include_input_data_metadata_json", False
            )
            if include_input_data_metadata_json == "true":
                include_input_data_metadata_json = True
            else:
                include_input_data_metadata_json = False
            add_notes = request.query_params.get("add_notes", False)
            if "export_type" in dict(request.query_params):
                export_type = request.query_params["export_type"]
            else:
                export_type = "CSV"
            tasks = Task.objects.filter(project_id__exact=project)

            if "task_status" in dict(request.query_params):
                task_status = request.query_params["task_status"]
                task_status = task_status.split(",")
                tasks = tasks.filter(task_status__in=task_status)

            if len(tasks) == 0:
                ret_dict = {"message": "No tasks in project!"}
                ret_status = status.HTTP_200_OK
                return Response(ret_dict, status=ret_status)
            tasks_list = []
            # required_annotators_per_task = project.required_annotators_per_task
            for task in tasks:
                ann_list = []
                task_dict = model_to_dict(task)
                if export_type != "JSON":
                    task_dict["data"]["task_status"] = task.task_status
                # Rename keys to match label studio converter
                # task_dict['id'] = task_dict['task_id']
                # del task_dict['task_id']
                correct_annotation = task.correct_annotation
                if correct_annotation is None and task.task_status in [
                    ANNOTATED,
                ]:
                    correct_annotation = task.annotations.all().filter(
                        annotation_type=ANNOTATOR_ANNOTATION
                    )[0]
                if correct_annotation is None and task.task_status in [
                    REVIEWED,
                ]:
                    correct_annotation = task.annotations.all().filter(
                        annotation_type=REVIEWER_ANNOTATION
                    )[0]

                annotator_email = ""
                # if correct_annotation is not None and required_annotators_per_task < 2:
                if correct_annotation is not None:
                    try:
                        annotator_email = correct_annotation.completed_by.email
                    except:
                        pass
                    task_dict["annotations"] = [correct_annotation]
                # elif required_annotators_per_task >= 2:
                #     all_ann = Annotation.objects.filter(task=task)
                #     for a in all_ann:
                #         ann_list.append(a)
                #     task_dict["annotations"] = ann_list
                else:
                    task_dict["annotations"] = []

                task_dict["data"]["annotator_email"] = annotator_email

                if include_input_data_metadata_json:
                    dataset_type = project.dataset_id.all()[0].dataset_type
                    dataset_model = getattr(dataset_models, dataset_type)
                    task_dict["data"]["input_data_metadata_json"] = (
                        dataset_model.objects.get(
                            pk=task_dict["input_data"]
                        ).metadata_json
                    )
                del task_dict["annotation_users"]
                del task_dict["review_user"]
                tasks_list.append(OrderedDict(task_dict))

            dataset_type = project.dataset_id.all()[0].dataset_type
            is_MultipleInteractionEvaluation = (
                project_type == "MultipleInteractionEvaluation"
            )
            is_ModelOutputEvaluation = project_type == "ModelOutputEvaluation"
            is_ModelInteractionEvaluation = project_type == "ModelInteractionEvaluation"
            for task in tasks_list:
                complete_result, notes = [], []
                for i in range(len(task["annotations"])):
                    a = task["annotations"][i]
                    annotation_result = a.result
                    annotation_result = (
                        json.loads(annotation_result)
                        if isinstance(annotation_result, str)
                        else annotation_result
                    )
                    uid = a.completed_by.email
                    try:
                        p_ann = a.parent_annotation.id
                    except Exception as e:
                        p_ann = None
                    single_dict = {
                        "user_id": uid,
                        "annotation_id": a.id,
                        "annotation_result": annotation_result,
                        "annotation_type": a.annotation_type,
                        "annotation_status": a.annotation_status,
                        "parent_annotation_id": p_ann,
                    }
                    complete_result.append(single_dict)
                    if add_notes:
                        notes.append(
                            {
                                "annotation_id": a.id,
                                "annotation_notes": a.annotation_notes,
                                "review_notes": a.review_notes,
                                "supercheck_notes": a.supercheck_notes,
                            }
                        )
                if is_MultipleInteractionEvaluation:
                    task["data"]["eval_form_json"] = complete_result
                elif is_ModelInteractionEvaluation:
                    task["data"]["eval_form_output_json"] = complete_result
                elif is_ModelOutputEvaluation:
                    task["data"]["form_output_json"] = complete_result
                else:
                    task["data"]["interactions_json"] = complete_result
                task["data"]["notes_json"] = notes
                del task["annotations"]
            return DataExport.generate_export_file(project, tasks_list, export_type)
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @swagger_auto_schema(method="get", responses={200: "No tasks to export!"})
    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "export_dataset_instance_id": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="A unique integer identifying the dataset instance",
                ),
            },
            description="Optional Post request body for projects which have save_type == new_record",
        ),
        responses={
            200: "No tasks to export! or SUCCESS!",
            404: "Project does not exist! or User does not exist!",
        },
    )
    @action(detail=True, methods=["POST", "GET"], name="Export Project")
    @project_is_archived
    @is_project_editor
    def project_export(self, request, pk=None, *args, **kwargs):
        """
        Export a project
        """
        try:
            project = Project.objects.get(pk=pk)
            project_type = dict(PROJECT_TYPE_CHOICES)[project.project_type]

            # Read registry to get output dataset model, and output fields
            registry_helper = ProjectRegistry.get_instance()
            output_dataset_info = registry_helper.get_output_dataset_and_fields(
                project_type
            )

            # If save_type is 'in_place'
            if output_dataset_info["save_type"] == "in_place":
                annotation_fields = output_dataset_info["fields"]["annotations"]

                if project.project_stage == REVIEW_STAGE:
                    tasks = Task.objects.filter(
                        project_id__exact=project, task_status__in=[REVIEWED]
                    )
                elif project.project_stage == SUPERCHECK_STAGE:
                    tasks = Task.objects.filter(
                        project_id__exact=project, task_status__in=[SUPER_CHECKED]
                    )
                else:
                    tasks = Task.objects.filter(
                        project_id__exact=project, task_status__in=[ANNOTATED]
                    )

                if len(tasks) == 0:
                    ret_dict = {"message": "No tasks to export!"}
                    ret_status = status.HTTP_200_OK
                    return Response(ret_dict, status=ret_status)

                # Call the async task export function for inplace functions
                export_project_in_place.delay(
                    annotation_fields=annotation_fields,
                    project_id=pk,
                    project_type=project_type,
                    get_request_data=dict(request.GET),
                )
            # If save_type is 'new_record'
            elif output_dataset_info["save_type"] == "new_record":
                export_dataset_instance_id = request.data.get(
                    "export_dataset_instance_id"
                )

                # If export_dataset_instance_id is not provided
                if export_dataset_instance_id is None:
                    ret_dict = {"message": "export_dataset_instance_id is required!"}
                    ret_status = status.HTTP_400_BAD_REQUEST
                    return Response(ret_dict, status=ret_status)

                annotation_fields = output_dataset_info["fields"]["annotations"]
                task_annotation_fields = []
                if "variable_parameters" in output_dataset_info["fields"]:
                    task_annotation_fields += output_dataset_info["fields"][
                        "variable_parameters"
                    ]
                if "copy_from_input" in output_dataset_info["fields"]:
                    task_annotation_fields += list(
                        output_dataset_info["fields"]["copy_from_input"].values()
                    )

                if project.project_stage == REVIEW_STAGE:
                    tasks = Task.objects.filter(
                        project_id__exact=project, task_status__in=[REVIEWED]
                    )
                elif project.project_stage == SUPERCHECK_STAGE:
                    tasks = Task.objects.filter(
                        project_id__exact=project, task_status__in=[SUPER_CHECKED]
                    )
                else:
                    tasks = Task.objects.filter(
                        project_id__exact=project, task_status__in=[ANNOTATED]
                    )
                if len(tasks) == 0:
                    ret_dict = {"message": "No tasks to export!"}
                    ret_status = status.HTTP_200_OK
                    return Response(ret_dict, status=ret_status)
                export_project_new_record.delay(
                    annotation_fields=annotation_fields,
                    project_id=pk,
                    project_type=project_type,
                    export_dataset_instance_id=export_dataset_instance_id,
                    task_annotation_fields=task_annotation_fields,
                    get_request_data=dict(request.GET),
                )

                # data_items.append(data_item)

                # TODO: implement bulk create if possible (only if non-hacky)
                # dataset_model.objects.bulk_create(data_items)
                # Saving data items to dataset in a loop
                # for item in data_items:
            # FIXME: Allow export multiple times
            # project.is_archived=True
            # project.save()
            ret_dict = {"message": "Project Export Started."}
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(detail=True, methods=["POST", "GET"], name="Publish Project")
    @project_is_archived
    @project_is_published
    @is_project_editor
    def project_publish(self, request, pk=None, *args, **kwargs):
        """
        Publish a project
        """
        try:
            project = Project.objects.get(pk=pk)

            if project.is_published:
                # Creating Notification
                title = f"{project.id}:{project.title} Project has been published"
                notification_type = "publish_project"
                notification_ids = get_userids_from_project_id(
                    project_id=pk,
                    annotators_bool=True,
                    reviewers_bool=True,
                    super_checkers_bool=True,
                    project_manager_bool=True,
                )
                createNotification(title, notification_type, notification_ids, pk)
                return Response(PROJECT_IS_PUBLISHED_ERROR, status=status.HTTP_200_OK)
            serializer = ProjectUsersSerializer(project, many=False)
            # ret_dict = serializer.data
            annotators = serializer.data["annotators"]

            if len(annotators) < project.required_annotators_per_task:
                ret_dict = {
                    "message": "Number of annotators is less than required annotators per task"
                }
                ret_status = status.HTTP_403_FORBIDDEN
                return Response(ret_dict, status=ret_status)
            # get all tasks of a project
            # tasks = Task.objects.filter(project_id=pk)

            # assign_users_to_tasks(tasks, annotators)

            # print("Here",task.annotation_users.all().count(), task.annotation_users.all())
            # for user in annotatorList:
            #     userEmail = user['email']

            #     send_mail("Annotation Tasks Assigned",
            #     f"Hello! You are assigned to tasks in the project {project.title}.",
            #     settings.DEFAULT_FROM_EMAIL, [userEmail],
            #     )

            # Task.objects.bulk_update(updated_tasks, ['annotation_users'])

            project.is_published = True
            project.published_at = datetime.now()
            project.save()

            ret_dict = {"message": "This project is published"}
            ret_status = status.HTTP_200_OK
        except Project.DoesNotExist:
            ret_dict = {"message": "Project does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        except User.DoesNotExist:
            ret_dict = {"message": "User does not exist!"}
            ret_status = status.HTTP_404_NOT_FOUND
        return Response(ret_dict, status=ret_status)

    @action(detail=False, methods=["GET"], name="Get language choices")
    def language_choices(self, request):
        return Response(LANG_CHOICES)

    @swagger_auto_schema(
        method="get",
        manual_parameters=[
            openapi.Parameter(
                "task_name",
                openapi.IN_QUERY,
                description=(
                    f"A task name to filter the tasks by. Allowed Tasks: {ALLOWED_CELERY_TASKS}"
                ),
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: "Returns the past task run history for a particular dataset instance and task name"
        },
    )
    @action(methods=["GET"], detail=True, name="Get all past instances of celery tasks")
    def get_async_task_results(self, request, pk):
        """
        View to get all past instances of celery tasks
        URL: /projects/<project_id>/get_async_task_results?task_name=<task-name>
        Accepted methods: GET

        Returns:
            A list of all past instances of celery tasks for a specific task using the project ID
        """

        # Get the task name from the request
        task_name = request.query_params.get("task_name")

        # Check if task name is in allowed task names list
        if task_name not in ALLOWED_CELERY_TASKS:
            return Response(
                {
                    "message": "Invalid task name for this app.",
                    "allowed_tasks": ALLOWED_CELERY_TASKS,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Handle 'create_parameter' task separately
        if task_name == "projects.tasks.create_parameters_for_task_creation":
            # Create the keyword argument for dataset instance ID
            project_id_keyword_arg = "'project_id': " + str(pk) + "}"
        else:
            # Create the keyword argument for dataset instance ID
            project_id_keyword_arg = "'project_id': " + "'" + str(pk) + "'"
        # Check the celery project export status
        task_queryset = TaskResult.objects.filter(
            task_name=task_name,
            task_kwargs__contains=project_id_keyword_arg,
        )

        # Check if queryset is empty
        if not task_queryset:
            return Response(
                {"message": "No results found"}, status=status.HTTP_204_NO_CONTENT
            )
        # Sort the task queryset by date and time
        task_queryset = task_queryset.order_by("-date_done")

        # Serialize the task queryset and return it to the frontend
        serializer = TaskResultSerializer(task_queryset, many=True)

        # Get a list of all dates
        dates = task_queryset.values_list("date_done", flat=True)
        status_list = task_queryset.values_list("status", flat=True)

        # Remove quotes from all statuses
        status_list = [status.replace("'", "") for status in status_list]

        # Extract date and time from the datetime object
        all_dates = [date.strftime("%d-%m-%Y") for date in dates]
        all_times = [date.strftime("%H:%M:%S") for date in dates]

        # Add the date, time and status to the serializer data
        for i in range(len(serializer.data)):
            serializer.data[i]["date"] = all_dates[i]
            serializer.data[i]["time"] = all_times[i]
            serializer.data[i]["status"] = status_list[i]
        return Response(serializer.data)

    @is_organization_owner_or_workspace_manager
    @action(
        detail=True,
        methods=["GET"],
        name="Update language field of task data to Project's target language",
        url_name="change_task_language_field_to_project_target_language",
    )
    def change_task_language_field_to_project_target_language(self, request, pk):
        project = Project.objects.get(pk=pk)
        tasks = Task.objects.filter(project_id=project)
        tasks_list = []
        for task in tasks:
            task_data = task.data
            task_data["output_language"] = project.tgt_language
            setattr(task, "data", task_data)
            tasks_list.append(task)

        Task.objects.bulk_update(tasks_list, ["data"])

        return Response(
            {"message": "language field of task data succesfully updated!"},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["POST"],
        url_name="set_password",
    )
    def set_password(self, request, pk=None):
        try:
            project = Project.objects.get(pk=pk)

            if "password" not in request.data:
                return Response(
                    {"error": "Password key is missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            password = request.data.get("password")

            if not password:
                return Response(
                    {"error": "Password not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                project.set_project_password(password)

            except Exception as e:
                return Response(
                    {"error": f"Failed to set the password : {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"message": "Password set Successfully"}, status=status.HTTP_200_OK
            )

        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=True,
        methods=["POST"],
        url_name="verify_password",
    )
    def verify_password(
        self,
        request,
        pk=None,
    ):
        try:
            project = Project.objects.get(pk=pk)

            if "password" not in request.data:
                return Response(
                    {"error": "Password key is missing"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            password = request.data.get("password")

            if not password:
                return Response(
                    {"error": "Password not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                if project.check_project_password(password):
                    current_user = request.data.get("user_id")
                    project.annotators.add(current_user)
                    project.save()
                    return Response(
                        {"message": "Authentication Successful"},
                        status=status.HTTP_200_OK,
                    )

                else:
                    return Response(
                        {"error": "Authentication Failed"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            except Exception as e:
                return Response(
                    {"error": f"Failed to authenticate project : {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=["POST"],
        url_path="allocate_tasks_to_user",
        name="Allocate tasks to user with role"
    )
    def allocate_tasks_to_user(self, request, *args, **kwargs):
        """
        Assign tasks to a user based on allocation_type:
        1 - Annotator
        2 - Reviewer
        3 - Super Checker (SC)
        """
        project_id = request.data.get("project_id")
        task_ids = request.data.get("taskIDs", [])
        user_id = request.data.get("userID")
        allocation_type = int(request.data.get("allocation_type", 1))  # default to 1

        if not all([project_id, task_ids, user_id, allocation_type]):
            return Response(
                {"message": "Missing one or more required fields: projectID, taskIDs, userID, allocation_type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(pk=project_id)
            user = User.objects.get(pk=user_id)
        except Project.DoesNotExist:
            return Response({"message": "Invalid project ID"}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"message": "Invalid user ID"}, status=status.HTTP_404_NOT_FOUND)

        valid_tasks = Task.objects.filter(id__in=task_ids, project_id=project_id)
        if not valid_tasks.exists():
            return Response({"message": "No valid tasks found for the given IDs and project"}, status=status.HTTP_404_NOT_FOUND)

        result = []
        for task in valid_tasks:
            # Assign user to appropriate field based on allocation_type
            if allocation_type == 1:
                task.annotation_users.add(user)
            elif allocation_type == 2:
                task.review_user = user
            elif allocation_type == 3:
                task.super_check_user = user

            # Check if user already has an annotation of this type on the task
            existing_annotation = Annotation_model.objects.filter(
                task=task,
                annotation_type=allocation_type,
                completed_by=user
            ).exists()

            if not existing_annotation:
                annotation = Annotation_model(
                    result=result,
                    task=task,
                    completed_by=user,
                    annotation_type=allocation_type
                )
                try:
                    annotation.save()
                except IntegrityError:
                    print(f"Annotation already exists for task {task.id}, user {user.email}, type {allocation_type}")

        return Response({"message": "Tasks successfully allocated"}, status=status.HTTP_200_OK)
