from projects.registry_helper import ProjectRegistry
from dataset import models as dataset_models
from users.utils import generate_random_string

ANNOTATION_REGISTRY_DICT = {
    "InstructionDrivenChat": {
        "interactions_json": {
            "to_name": "instruction_data",
            "from_name": ["prompt", "output"],
        }
    },
    "MultipleLLMInstructionDrivenChat": {
        "model_interactions": {
            "to_name": "instruction_data",
            "from_name": ["prompt", "output", "preferred_response", "model"],
        }
    }
}


def convert_prediction_json_to_annotation_result(
    prediction_json, speakers_json, audio_duration, index, is_acoustic=False
):
    """
    Convert prediction_json and transcribed_json to annotation_result
    """

    result = []
    if prediction_json == None:
        return result

    for idx, val in enumerate(prediction_json):
        label_dict = {
            "origin": "manual",
            "to_name": "audio_url",
            "from_name": "labels",
            "original_length": audio_duration,
        }
        text_dict = {
            "origin": "manual",
            "to_name": "audio_url",
            "from_name": "transcribed_json",
            "original_length": audio_duration,
        }
        if is_acoustic:
            text_dict["from_name"] = "verbatim_transcribed_json"
        id = f"anudesh_{index}s{idx}s{generate_random_string(13-len(str(idx)))}"
        label_dict["id"] = id
        text_dict["id"] = id
        label_dict["type"] = "labels"
        text_dict["type"] = "textarea"

        value_labels = {
            "start": val["start"],
            "end": val["end"],
            "labels": [
                next(
                    speaker
                    for speaker in speakers_json
                    if speaker["speaker_id"] == val["speaker_id"]
                )["name"]
            ],
        }
        value_text = {"start": val["start"], "end": val["end"], "text": [val["text"]]}

        label_dict["value"] = value_labels
        text_dict["value"] = value_text
        result.append(label_dict)
        result.append(text_dict)

    return result


def convert_conversation_json_to_annotation_result(conversation_json, idx):
    result = []
    for i in range(len(conversation_json)):
        for j in range(len(conversation_json[i]["sentences"])):
            id = f"anudesh_{idx}s{i}s{j}s{generate_random_string(15-len(str(i))-len(str(j)))}"
            text_dict = {
                "id": id,
                "type": "textarea",
                "value": {"text": [conversation_json[i]["sentences"][j]]},
                "origin": "manual",
                "to_name": f"dialog_{i}_{j}",
                "from_name": f"output_{i}_{j}",
            }
            result.append(text_dict)

    return result


def draft_data_json_to_annotation_result(draft_data_json, project_type, pk=None):
    registry_helper = ProjectRegistry.get_instance()
    input_dataset_info = registry_helper.get_input_dataset_and_fields(project_type)
    dataset_model = getattr(dataset_models, input_dataset_info["dataset_type"])
    try:
        dataset_item = dataset_model.objects.get(pk=pk)
    except:
        pass
    result = []
    idx = 0
    for field, value in draft_data_json.items():
        try:
            id = f"anudesh_{idx}g{generate_random_string(13-len(str(idx)))}"
            field_dict = {
                "id": id,
                "origin": "manual",
                "type": ANNOTATION_REGISTRY_DICT[project_type][field]["type"],
                "to_name": ANNOTATION_REGISTRY_DICT[project_type][field]["to_name"],
                "from_name": ANNOTATION_REGISTRY_DICT[project_type][field]["from_name"],
            }
            field_type = ANNOTATION_REGISTRY_DICT[project_type][field]["type"]
            ans = []
            if field == "conversation_json":
                ans = convert_conversation_json_to_annotation_result(value, idx)
            elif field == "transcribed_json" or field == "prediction_json":
                ans = convert_prediction_json_to_annotation_result(
                    value,
                    dataset_item.speakers_json,
                    dataset_item.audio_duration,
                    idx,
                    project_type == "AcousticNormalisedTranscriptionEditing",
                )
            else:
                if field_type == "textarea":
                    field_dict["value"] = {"text": [value]}
                elif field_type == "choices":
                    field_dict["value"] = {"choices": [value]}
                elif field_type == "taxonomy":
                    field_dict["value"] = {"taxonomy": [value.split(",")]}

                ans.append(field_dict)

            result.extend(ans)
            idx += 1
        except:
            pass

    if project_type == "InstructionDrivenChat" or project_type == "MultipleLLMInstructionDrivenChat":
        result = dataset_item.draft_data_json

    return result
