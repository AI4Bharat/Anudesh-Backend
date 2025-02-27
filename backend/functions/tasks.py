import datetime
import zipfile
import threading
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import pandas as pd
from celery import shared_task
from dataset import models as dataset_models
from organizations.models import Organization
from projects.models import Project
from projects.utils import (
    convert_seconds_to_hours,
    get_audio_project_types,
    get_audio_transcription_duration,
    calculate_word_error_rate_between_two_llm_prompts,
    ocr_word_count,
    get_not_null_audio_transcription_duration,
)
from projects.views import get_task_count_unassigned, ProjectViewSet
from anudesh_backend import settings
from tasks.models import (
    Annotation,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
    REVIEWED,
    SUPER_CHECKED,
    Task,
    ANNOTATED,
)
from tasks.views import SentenceOperationViewSet
from users.models import User
from django.core.mail import EmailMessage
from anudesh_backend.locks import Lock
from utils.blob_functions import (
    extract_account_name,
    extract_account_key,
    extract_endpoint_suffix,
    test_container_connection,
)
from utils.custom_bulk_create import multi_inheritance_table_bulk_insert
from workspaces.models import Workspace

from django.db import transaction, DataError, IntegrityError
from dataset.models import DatasetInstance
from django.apps import apps
from rest_framework.test import APIRequestFactory
from django.http import QueryDict
from rest_framework.request import Request
from dataset.models import LANGUAGE_CHOICES
import os
import tempfile


## CELERY SHARED TASKS


@shared_task(bind=True)
def populate_draft_data_json(self, pk, fields_list):
    try:
        dataset_instance = DatasetInstance.objects.get(pk=pk)
    except Exception as error:
        return error
    dataset_type = dataset_instance.dataset_type
    dataset_model = apps.get_model("dataset", dataset_type)
    dataset_items = dataset_model.objects.filter(instance_id=dataset_instance)
    cnt = 0
    for dataset_item in dataset_items:
        new_draft_data_json = {}
        for field in fields_list:
            try:
                new_draft_data_json[field] = getattr(dataset_item, field)
                if new_draft_data_json[field] == None:
                    del new_draft_data_json[field]
            except:
                pass

        if new_draft_data_json != {}:
            dataset_item.draft_data_json = new_draft_data_json
            dataset_item.save()
            cnt += 1

    return f"successfully populated {cnt} dataset items with draft_data_json"


# The flow for project_reports- schedule_mail_for_project_reports -> get_proj_objs, get_stats ->
# get_modified_stats_result, get_stats_helper -> update_meta_stats -> calculate_ced_between_two_annotations,
# calculate_wer_between_two_annotations, get_most_recent_annotation.
@shared_task(queue="reports")
def schedule_mail_for_project_reports(
    project_type,
    user_id,
    anno_stats,
    meta_stats,
    complete_stats,
    workspace_level_reports,
    organization_level_reports,
    dataset_level_reports,
    wid,
    oid,
    did,
    language,
):
    task_name = (
        "schedule_mail_for_project_reports"
        + str(project_type)
        + str(anno_stats)
        + str(meta_stats)
        + str(complete_stats)
        + str(workspace_level_reports)
        + str(organization_level_reports)
        + str(dataset_level_reports)
        + str(wid)
        + str(oid)
        + str(did)
        + str(language)
    )
    proj_objs = get_proj_objs(
        workspace_level_reports,
        organization_level_reports,
        dataset_level_reports,
        project_type,
        wid,
        oid,
        did,
        language,
    )
    if len(proj_objs) == 0:
        celery_lock = Lock(user_id, task_name)
        try:
            celery_lock.releaseLock()
        except Exception as e:
            print(f"Error while releasing the lock for {task_name}: {str(e)}")
        print("No projects found")
        return 0
    user = User.objects.get(id=user_id)
    result = get_stats(
        proj_objs, anno_stats, meta_stats, complete_stats, project_type, user
    )
    df = pd.DataFrame.from_dict(result)
    transposed_df = df.transpose()
    content = transposed_df.to_csv(index=True)
    content_type = "text/csv"

    if workspace_level_reports:
        workspace = Workspace.objects.filter(id=wid)
        name = workspace[0].workspace_name
        type = "workspace"
        filename = f"{name}_user_analytics.csv"
    elif dataset_level_reports:
        dataset = DatasetInstance.objects.filter(instance_id=did)
        name = dataset[0].instance_name
        type = "dataset"
        filename = f"{name}_user_analytics.csv"
    else:
        organization = Organization.objects.filter(id=oid)
        name = organization[0].title
        type = "organization"
        filename = f"{name}_user_analytics.csv"

    message = (
        "Dear "
        + str(user.username)
        + f",\nYour project reports for the {type}"
        + f"{name}"
        + " are ready.\n Thanks for contributing on Anudesh!"
        + "\nProject Type: "
        + f"{project_type}"
    )

    email = EmailMessage(
        f"{name}" + " Payment Reports",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        attachments=[(filename, content, content_type)],
    )
    try:
        email.send()
    except Exception as e:
        print(f"An error occurred while sending email: {e}")
    celery_lock = Lock(user_id, task_name)
    try:
        celery_lock.releaseLock()
    except Exception as e:
        print(f"Error while releasing the lock for {task_name}: {str(e)}")
    print(f"Email sent successfully - {user_id}")


def get_stats(proj_objs, anno_stats, meta_stats, complete_stats, project_type, user):
    result = {}
    for proj in proj_objs:
        annotations = Annotation.objects.filter(task__project_id=proj.id)
        (
            result_ann_anno_stats,
            result_rev_anno_stats,
            result_sup_anno_stats,
            result_ann_meta_stats,
            result_rev_meta_stats,
            result_sup_meta_stats,
            average_ann_vs_rev_WER,
            average_rev_vs_sup_WER,
            average_ann_vs_sup_WER,
        ) = get_stats_definitions()
        for ann_obj in annotations:
            if ann_obj.annotation_type == ANNOTATOR_ANNOTATION:
                try:
                    get_stats_helper(
                        anno_stats,
                        meta_stats,
                        complete_stats,
                        result_ann_anno_stats,
                        result_ann_meta_stats,
                        ann_obj,
                        project_type,
                        average_ann_vs_rev_WER,
                        average_rev_vs_sup_WER,
                        average_ann_vs_sup_WER,
                    )
                except:
                    continue
            elif ann_obj.annotation_type == REVIEWER_ANNOTATION:
                try:
                    get_stats_helper(
                        anno_stats,
                        meta_stats,
                        complete_stats,
                        result_rev_anno_stats,
                        result_rev_meta_stats,
                        ann_obj,
                        project_type,
                        average_ann_vs_rev_WER,
                        average_rev_vs_sup_WER,
                        average_ann_vs_sup_WER,
                    )
                except:
                    continue
            elif ann_obj.annotation_type == SUPER_CHECKER_ANNOTATION:
                try:
                    get_stats_helper(
                        anno_stats,
                        meta_stats,
                        complete_stats,
                        result_sup_anno_stats,
                        result_sup_meta_stats,
                        ann_obj,
                        project_type,
                        average_ann_vs_rev_WER,
                        average_rev_vs_sup_WER,
                        average_ann_vs_sup_WER,
                    )
                except:
                    continue
        result[f"{proj.id} - {proj.title}"] = get_modified_stats_result(
            result_ann_meta_stats,
            result_rev_meta_stats,
            result_sup_meta_stats,
            result_ann_anno_stats,
            result_rev_anno_stats,
            result_sup_anno_stats,
            anno_stats,
            meta_stats,
            complete_stats,
            average_ann_vs_rev_WER,
            average_rev_vs_sup_WER,
            average_ann_vs_sup_WER,
            proj.id,
            user,
        )

    return result


def get_stats_definitions():
    result_ann_anno_stats = {
        "unlabeled": 0,
        "labeled": 0,
        "skipped": 0,
        "draft": 0,
        "to_be_revised": 0,
    }
    result_rev_anno_stats = {
        "unreviewed": 0,
        "skipped": 0,
        "draft": 0,
        "to_be_revised": 0,
        "accepted": 0,
        "accepted_with_minor_changes": 0,
        "accepted_with_major_changes": 0,
        "rejected": 0,
    }
    result_sup_anno_stats = {
        "unvalidated": 0,
        "skipped": 0,
        "draft": 0,
        "validated": 0,
        "validated_with_changes": 0,
        "rejected": 0,
    }
    result_ann_meta_stats = {
        "unlabeled": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "skipped": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "draft": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "labeled": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "to_be_revised": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
    }
    result_rev_meta_stats = {
        "unreviewed": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "skipped": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "draft": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "to_be_revised": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "accepted": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "accepted_with_minor_changes": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "accepted_with_major_changes": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "rejected": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
    }
    result_sup_meta_stats = {
        "unvalidated": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "skipped": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "draft": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "validated": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "validated_with_changes": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
        "rejected": {
            "Total_Words_in_Prompts": 0,
            "Number_of_Prompt-Output_Pairs": 0,
            "Avg_Word_Count_Per_Prompt": 0,
            "Avg_Word_Count_Per_Output": 0,
        },
    }
    return (
        result_ann_anno_stats,
        result_rev_anno_stats,
        result_sup_anno_stats,
        result_ann_meta_stats,
        result_rev_meta_stats,
        result_sup_meta_stats,
        [],
        [],
        [],
    )


def get_modified_stats_result(
    result_ann_meta_stats,
    result_rev_meta_stats,
    result_sup_meta_stats,
    result_ann_anno_stats,
    result_rev_anno_stats,
    result_sup_anno_stats,
    anno_stats,
    meta_stats,
    complete_stats,
    average_ann_vs_rev_WER,
    average_rev_vs_sup_WER,
    average_ann_vs_sup_WER,
    proj_id,
    user,
):
    result = {}
    if anno_stats or complete_stats:
        for key, value in result_ann_anno_stats.items():
            result[f"Annotator - {key.replace('_', ' ').title()} Annotations"] = value
        for key, value in result_rev_anno_stats.items():
            result[f"Reviewer - {key.replace('_', ' ').title()} Annotations"] = value
        for key, value in result_sup_anno_stats.items():
            result[f"Superchecker - {key.replace('_', ' ').title()} Annotations"] = (
                value
            )
    if meta_stats or complete_stats:
        for key, value in result_ann_meta_stats.items():
            for sub_key in value.keys():
                result[f"Annotator - {key.replace('_', ' ').title()} {sub_key}"] = (
                    value[sub_key]
                )
        for key, value in result_rev_meta_stats.items():
            for sub_key in value.keys():
                result[f"Reviewer - {key.replace('_', ' ').title()} {sub_key}"] = value[
                    sub_key
                ]
        for key, value in result_sup_meta_stats.items():
            for sub_key in value.keys():
                result[f"Superchecker - {key.replace('_', ' ').title()} {sub_key}"] = (
                    value[sub_key]
                )

    # adding unassigned tasks count
    result["Annotator - Unassigned Tasks"] = get_task_count_unassigned(proj_id, user)
    result["Reviewer - Unassigned Tasks"] = (
        Task.objects.filter(project_id=proj_id)
        .filter(task_status=ANNOTATED)
        .filter(review_user__isnull=True)
        .exclude(annotation_users=user.id)
        .count()
    )
    result["Superchecker - Unassigned Tasks"] = (
        Task.objects.filter(project_id=proj_id)
        .filter(task_status=REVIEWED)
        .filter(super_check_user__isnull=True)
        .exclude(annotation_users=user.id)
        .exclude(review_user=user.id)
        .count()
    )
    result["Average Annotator VS Reviewer Word Error Rate"] = "{:.2f}".format(
        get_average_of_a_list(average_ann_vs_rev_WER)
    )
    result["Average Reviewer VS Superchecker Word Error Rate"] = "{:.2f}".format(
        get_average_of_a_list(average_rev_vs_sup_WER)
    )
    result["Average Annotator VS Superchecker Word Error Rate"] = "{:.2f}".format(
        get_average_of_a_list(average_rev_vs_sup_WER)
    )
    return result


def get_average_of_a_list(arr):
    if not isinstance(arr, list):
        return 0
    total_sum = 0
    total_length = 0
    for num in arr:
        if isinstance(num, int) or isinstance(num, float):
            total_sum += num
            total_length += 1
    return total_sum / total_length if total_length > 0 else 0


def get_proj_objs(
    workspace_level_reports,
    organization_level_reports,
    dataset_level_reports,
    project_type,
    wid,
    oid,
    did,
    language,
):
    if workspace_level_reports:
        if project_type:
            LANG_CHOICES_DICT = dict(LANGUAGE_CHOICES)
            if language in LANG_CHOICES_DICT:
                proj_objs = Project.objects.filter(
                    workspace_id=wid,
                    project_type=project_type,
                    tgt_language=language,
                )
            else:
                proj_objs = Project.objects.filter(
                    workspace_id=wid, project_type=project_type
                )
        else:
            proj_objs = Project.objects.filter(workspace_id=wid)
    elif organization_level_reports:
        if project_type:
            LANG_CHOICES_DICT = dict(LANGUAGE_CHOICES)
            if language in LANG_CHOICES_DICT:
                proj_objs = Project.objects.filter(
                    organization_id=oid,
                    project_type=project_type,
                    tgt_language=language,
                )
            else:
                proj_objs = Project.objects.filter(
                    organization_id=oid, project_type=project_type
                )
        else:
            proj_objs = Project.objects.filter(organization_id=oid)
    elif dataset_level_reports:
        if project_type:
            LANG_CHOICES_DICT = dict(LANGUAGE_CHOICES)
            if language in LANG_CHOICES_DICT:
                proj_objs = Project.objects.filter(
                    dataset_id=did,
                    project_type=project_type,
                    tgt_language=language,
                )
            else:
                proj_objs = Project.objects.filter(
                    dataset_id=did, project_type=project_type
                )
        else:
            proj_objs = Project.objects.filter(dataset_id=did)
    else:
        proj_objs = {}
    return proj_objs


def get_stats_helper(
    anno_stats,
    meta_stats,
    complete_stats,
    result_anno_stats,
    result_meta_stats,
    ann_obj,
    project_type,
    average_ann_vs_rev_WER,
    average_rev_vs_sup_WER,
    average_ann_vs_sup_WER,
):
    task_obj = ann_obj.task
    task_data = task_obj.data

    if anno_stats or complete_stats:
        update_anno_stats(result_anno_stats, ann_obj, anno_stats)
        if anno_stats:
            return 0
    update_meta_stats(
        result_meta_stats,
        ann_obj,
        project_type,
    )
    if task_obj.task_status == REVIEWED:
        if ann_obj.annotation_type == REVIEWER_ANNOTATION:
            try:
                average_ann_vs_rev_WER.append(
                    calculate_wer_between_two_annotations(
                        get_most_recent_annotation(ann_obj).result,
                        get_most_recent_annotation(ann_obj.parent_annotation).result,
                    )
                )
            except Exception as error:
                pass
    elif task_obj.task_status == SUPER_CHECKED:
        if ann_obj.annotation_type == SUPER_CHECKER_ANNOTATION:
            try:
                average_ann_vs_rev_WER.append(
                    calculate_wer_between_two_annotations(
                        get_most_recent_annotation(ann_obj.parent_annotation).result,
                        get_most_recent_annotation(
                            ann_obj.parent_annotation.parent_annotation
                        ).result,
                    )
                )
            except Exception as error:
                pass
            try:
                average_rev_vs_sup_WER.append(
                    calculate_wer_between_two_annotations(
                        get_most_recent_annotation(ann_obj).result,
                        get_most_recent_annotation(ann_obj.parent_annotation).result,
                    )
                )
            except Exception as error:
                pass

    return 0


def update_anno_stats(result_anno_stats, ann_obj, anno_stats):
    result_anno_stats[ann_obj.annotation_status] += 1
    return 0 if anno_stats else None


def update_meta_stats(result_meta_stats, ann_obj, project_type):
    if "InstructionDrivenChat" in project_type:
        result_meta_stats_ann = ann_obj.meta_stats
        if result_meta_stats_ann:
            result_meta_stats[ann_obj.annotation_status]["Total_Words_in_Prompts"] += (
                result_meta_stats_ann["prompts_word_count"]
                if "prompts_word_count" in result_meta_stats_ann
                else 0
            )
            result_meta_stats[ann_obj.annotation_status][
                "Number_of_Prompt-Output_Pairs"
            ] += (
                result_meta_stats_ann["number_of_turns"]
                if "number_of_turns" in result_meta_stats_ann
                else 0
            )
            result_meta_stats[ann_obj.annotation_status][
                "Avg_Word_Count_Per_Prompt"
            ] += (
                result_meta_stats_ann["avg_word_count_per_prompt"]
                if "avg_word_count_per_prompt" in result_meta_stats_ann
                else 0
            )
            result_meta_stats[ann_obj.annotation_status][
                "Avg_Word_Count_Per_Output"
            ] += (
                result_meta_stats_ann["avg_word_count_per_output"]
                if "avg_word_count_per_output" in result_meta_stats_ann
                else 0
            )


def calculate_ced_between_two_annotations(annotation1, annotation2):
    sentence_operation = SentenceOperationViewSet()
    ced_list = []
    for i in range(len(annotation1.result)):
        if "value" in annotation1.result[i]:
            if "text" in annotation1.result[i]["value"]:
                str1 = annotation1.result[i]["value"]["text"]
            else:
                continue
        else:
            continue
        if "value" in annotation2.result[i]:
            if "text" in annotation2.result[i]["value"]:
                str2 = annotation2.result[i]["value"]["text"]
            else:
                continue
        else:
            continue
        data = {"sentence1": str1, "sentence2": str2}
        try:
            char_level_distance = (
                sentence_operation.calculate_normalized_character_level_edit_distance(
                    data
                )
            )
            ced_list.append(
                char_level_distance.data["normalized_character_level_edit_distance"]
            )
        except Exception as e:
            continue
    return ced_list


def calculate_wer_between_two_annotations(annotation1, annotation2):
    try:
        return calculate_word_error_rate_between_two_llm_prompts(
            annotation1, annotation2
        )
    except Exception as e:
        return 0


def get_most_recent_annotation(annotation):
    duplicate_ann = Annotation.objects.filter(
        task=annotation.task, annotation_type=annotation.annotation_type
    )
    for ann in duplicate_ann:
        if annotation.updated_at < ann.updated_at:
            annotation = ann
    return annotation


@shared_task(bind=True)
def schedule_mail_to_download_all_projects(
    self, workspace_level_projects, dataset_level_projects, wid, did, user_id
):
    task_name = (
        "schedule_mail_to_download_all_projects"
        + str(workspace_level_projects)
        + str(dataset_level_projects)
        + str(wid)
        + str(did)
    )
    download_lock = threading.Lock()
    download_lock.acquire()
    proj_objs = get_proj_objs(
        workspace_level_projects,
        False,
        dataset_level_projects,
        None,
        wid,
        0,
        did,
    )
    if len(proj_objs) == 0 and workspace_level_projects:
        print(f"No projects found for workspace id- {wid}")
        celery_lock = Lock(user_id, task_name)
        try:
            celery_lock.releaseLock()
        except Exception as e:
            print(f"Error while releasing the lock for {task_name}: {str(e)}")
        return 0
    elif len(proj_objs) == 0 and dataset_level_projects:
        print(f"No projects found for dataset id- {did}")
        celery_lock = Lock(user_id, task_name)
        try:
            celery_lock.releaseLock()
        except Exception as e:
            print(f"Error while releasing the lock for {task_name}: {str(e)}")
        return 0
    user = User.objects.get(id=user_id)
    with tempfile.TemporaryDirectory() as temp_dir:
        for proj in proj_objs:
            proj_view_set_obj = ProjectViewSet()
            factory = APIRequestFactory()
            url = f"/projects/{proj.id}/download"
            query_params = QueryDict(mutable=True)
            query_params["include_input_data_metadata_json"] = "true"
            query_params["export_type"] = "CSV"
            query_params["task_status"] = (
                "incomplete,annotated,reviewed,super_checked,exported"
            )
            custom_request = Request(factory.get(url, data=query_params, timeout=15))
            custom_request.user = user
            try:
                proj_file = proj_view_set_obj.download(custom_request, proj.id)
            except Exception as e:
                print(f"Downloading project timed out, Project id- {proj.id}")
                continue
            file_path = os.path.join(temp_dir, f"{proj.id} - {proj.title}.csv")
            with open(file_path, "wb") as f:
                f.write(proj_file.content)
        url = upload_all_projects_to_blob_and_get_url(temp_dir)
    if url:
        message = (
            "Dear "
            + str(user.username)
            + f",\nYou can download all the projects by clicking on- "
            + f"{url}"
            + " This link is active only for 1 hour.\n Thanks for contributing on Anudesh!"
        )
        email = EmailMessage(
            f"{user.username}" + "- Link to download all projects",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        try:
            email.send()
        except Exception as e:
            print(f"An error occurred while sending email: {e}")
            return 0
        download_lock.release()
        celery_lock = Lock(user_id, task_name)
        try:
            celery_lock.releaseLock()
        except Exception as e:
            print(f"Error while releasing the lock for {task_name}: {str(e)}")
        print(f"Email sent successfully - {user_id}")
    else:
        download_lock.release()
        celery_lock = Lock(user_id, task_name)
        try:
            celery_lock.releaseLock()
        except Exception as e:
            print(f"Error while releasing the lock for {task_name}: {str(e)}")
        print(url)


def upload_all_projects_to_blob_and_get_url(csv_files_directory):
    date_time_string = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_file_name = f"output_all_projects - {date_time_string}.zip"
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
    CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS = os.getenv(
        "CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS"
    )
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS
        )
    except Exception as e:
        return "Error in connecting to blob_service_client or container_client"
    if not test_container_connection(
        AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS
    ):
        print("Azure Blob Storage connection test failed. Exiting...")
        return "test_container_connection failed"
    blob_url = ""
    if os.path.exists(csv_files_directory):
        zip_file_path_on_disk = csv_files_directory + "/" + f"{zip_file_name}"
        try:
            with zipfile.ZipFile(
                zip_file_path_on_disk, "w", zipfile.ZIP_DEFLATED
            ) as zipf:
                for root, dirs, files in os.walk(csv_files_directory):
                    for file in files:
                        if file.endswith(".csv"):
                            file_path = os.path.join(root, file)
                            zipf.write(
                                file_path,
                                os.path.relpath(file_path, csv_files_directory),
                            )
        except Exception as e:
            return "Error in creating zip file"
        blob_client = container_client.get_blob_client(zip_file_name)
        with open(zip_file_path_on_disk, "rb") as file:
            blob_client.upload_blob(file, blob_type="BlockBlob")
        try:
            expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
            account_name = extract_account_name(AZURE_STORAGE_CONNECTION_STRING)
            endpoint_suffix = extract_endpoint_suffix(AZURE_STORAGE_CONNECTION_STRING)
            sas_token = generate_blob_sas(
                container_name=CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS,
                blob_name=blob_client.blob_name,
                account_name=account_name,
                account_key=extract_account_key(AZURE_STORAGE_CONNECTION_STRING),
                permission=BlobSasPermissions(read=True),
                expiry=expiry,
            )
        except Exception as e:
            return "Error in generating url"
        blob_url = f"https://{account_name}.blob.{endpoint_suffix}/{CONTAINER_NAME_FOR_DOWNLOAD_ALL_PROJECTS}/{blob_client.blob_name}?{sas_token}"
    return blob_url
