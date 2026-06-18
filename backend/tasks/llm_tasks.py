from celery import shared_task


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_llm_task(self, annotation_id, prompt):
    from tasks.models import Annotation
    from tasks.views import get_llm_output
    from tasks.utils import compute_meta_stats_for_instruction_driven_chat
    from django.db import transaction

    try:
        with transaction.atomic():
            annotation_obj = Annotation.objects.select_for_update().get(id=annotation_id)

            output = get_llm_output(
                prompt,
                annotation_obj.task,
                annotation_obj,
                annotation_obj.task.project_id.metadata_json,
            )

            if output in (-1, None, "Null", "None", "", " "):
                raise Exception("LLM returned empty or invalid output")

            annotation_obj.result.append({"prompt": prompt, "output": output})
            annotation_obj.meta_stats = compute_meta_stats_for_instruction_driven_chat(
                annotation_obj.result
            )
            annotation_obj.save(update_fields=["result", "meta_stats", "updated_at"])

        return {"annotation_result": annotation_obj.result}

    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def run_all_llm_task(self, annotation_id, prompt, prompt_output_pair_id):
    from tasks.models import Annotation
    from tasks.views import get_all_llm_output
    from tasks.utils import compute_meta_stats_for_multiple_llm_idc
    from django.db import transaction
    from rest_framework.response import Response as DRFResponse

    try:
        with transaction.atomic():
            annotation_obj = Annotation.objects.select_for_update().get(id=annotation_id)

            if not annotation_obj.result:
                annotation_obj.result.append({"eval_form": [], "model_interactions": []})
            result_entry = annotation_obj.result[0]
            if "model_interactions" not in result_entry:
                result_entry["model_interactions"] = []

            output_result = get_all_llm_output(
                prompt,
                annotation_obj.task,
                annotation_obj,
                annotation_obj.task.project_id.metadata_json,
                annotation_obj.task.data.get("model", []),
            )

            if output_result in (-1, None):
                raise Exception("LLM returned empty or invalid output")
            if isinstance(output_result, DRFResponse):
                raise Exception(output_result.data.get("message", "LLM error"))

            for model_name, model_output in output_result.items():
                new_interaction = {
                    "prompt": prompt,
                    "output": model_output,
                    "preferred_response": False,
                    "prompt_output_pair_id": prompt_output_pair_id,
                }
                model_found = False
                for model_entry in result_entry["model_interactions"]:
                    if model_entry.get("model_name") == model_name:
                        model_entry["interaction_json"].append(new_interaction)
                        model_found = True
                        break
                if not model_found:
                    result_entry["model_interactions"].append({
                        "model_name": model_name,
                        "interaction_json": [new_interaction],
                    })

            annotation_obj.meta_stats = compute_meta_stats_for_multiple_llm_idc(
                annotation_obj.result
            )
            annotation_obj.save(update_fields=["result", "meta_stats", "updated_at"])

        return {"annotation_result": annotation_obj.result}

    except Exception as exc:
        raise self.retry(exc=exc)
