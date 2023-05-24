from projects.registry_helper import ProjectRegistry
from dataset import models as dataset_models

ANNOTATION_REGISTRY_DICT={
    "MonolingualTranslation":{
        "output_text":{
            "to_name":"input_text",
            "from_name":"output_text",
            "type":"textarea",
        },
    },
    "TranslationEditing":{
        "output_text":{
            "to_name":"input_text",
            "from_name":"output_text",
            "type":"textarea",
        },
    },
    "SemanticTextualSimilarity_Scale5":{
        "rating":{
            "to_name": "output_text",
            "from_name": "rating",
            "type":"choices",
        },
    },
    "ContextualTranslationEditing":{
        "output_text":{
            "to_name":"input_text",
            "from_name":"output_text",
            "type":"textarea",
        },
    },
    "ContextualSentenceVerification":{
        "corrected_text":{
            "to_name":"text",
            "from_name":"corrected_text",
            "type":"textarea",
        },
        "quality_status":{
            "to_name":"text",
            "from_name":"quality_status",
            "type":"choices",
        },
    },
    "ContextualSentenceVerificationAndDomainClassification":{
        "corrected_text":{
            "to_name":"text",
            "from_name":"corrected_text",
            "type":"textarea",
        },
        "quality_status":{
            "to_name":"text",
            "from_name":"quality_status",
            "type":"choices",
        },
        "domain":{
            "to_name":"text",
            "from_name":"domain",
            "type":"taxonomy",
        },

    },
    "ConversationTranslation":{
        "conversation_json":{
            "to_name":"dialog_i_j",
            "from_name":"output_i_j",
            "type":"textarea",
        },
    },
    "ConversationTranslationEditing":{
        "conversation_json":{
            "to_name":"dialog_i_j",
            "from_name":"output_i_j",
            "type":"textarea",
        },
    },
    "ConversationVerification":{
        "conversation_json":{
            "to_name":"dialog_i_j",
            "from_name":"output_i_j",
            "type":"textarea",
        },
        "conversation_quality_status":{
            "to_name": "quality_status",
            "from_name": "quality_status",
            "type":"choices",
        }
    },
    "AudioTranscription":{
        "transcribed_json":{
            "to_name": "audio_url",
            "from_name": ["labels","transcribed_json"],
            "type":["labels","textarea"]
        },
    },
    "AudioTranscriptionEditing":{
        "transcribed_json":{
            "to_name": "audio_url",
            "from_name": ["labels","transcribed_json"],
            "type":["labels","textarea"]
        },

    },
    "AudioSegmentation":{
        "prediction_json":{
            "to_name": "audio_url",
            "from_name": "labels",
            "type":"labels",
        },
    }

}



def draft_data_json_to_annotation_result(draft_data_json,project_type,pk=None):
    registry_helper=ProjectRegistry.get_instance()
    input_dataset_info=registry_helper.get_input_dataset_and_fields(project_type)
    dataset_model=getattr(dataset_models,input_dataset_info["dataset_type"])