"""
Module to store Django REST Framework Serializers for dataset related models
"""

from django_celery_results.models import TaskResult
from rest_framework import serializers

from .models import *


class DatasetInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetInstance
        fields = "__all__"


class DatasetInstanceUploadSerializer(serializers.Serializer):
    dataset = serializers.FileField()

    class Meta:
        fields = ["dataset"]


class DatasetItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetBase
        fields = ["instance_id"]


class SentenceTextSerializer(serializers.ModelSerializer):
    """
    Serializer for SentenceText data
    """

    metadata_json = serializers.JSONField()

    class Meta:
        model = SentenceText
        fields = "__all__"


class TranslationPairSerializer(serializers.ModelSerializer):
    """
    Serializer for TranslationPair data
    """

    metadata_json = serializers.JSONField()

    class Meta:
        model = TranslationPair
        fields = "__all__"


class OCRDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for OCRDocument data
    """

    class Meta:
        model = OCRDocument
        fields = "__all__"


class BlockTextSerializer(serializers.ModelSerializer):
    """
    Serializer for BlockText data
    """

    class Meta:
        model = BlockText
        fields = "__all__"


class TaskResultSerializer(serializers.ModelSerializer):
    """
    Serializer for TaskResult data
    """

    class Meta:
        model = TaskResult
        fields = "__all__"


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation data
    """

    metadata_json = serializers.JSONField()

    class Meta:
        model = Conversation
        fields = "__all__"


class SpeechConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Speech Conversation
    """

    metadata_json = serializers.JSONField()

    class Meta:
        model = SpeechConversation
        fields = "__all__"


class PromptBaseSerializer(serializers.ModelSerializer):
    """
    Serializer for Prompt Base
    """

    class Meta:
        model = PromptBase
        fields = "__all__"


class PromptAnswerSerializer(serializers.ModelSerializer):
    """
    Serializer for Prompt Answer
    """

    class Meta:
        model = PromptAnswer
        fields = "__all__"


class PromptAnswerEvaluationSerializer(serializers.ModelSerializer):
    """
    Serializer for Prompt Answer Evaluation
    """

    class Meta:
        model = PromptAnswerEvaluation
        fields = "__all__"


class InstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instruction
        fields = "__all__"


class InteractionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = "__all__"


# Define a mapping between dataset instance type and serializer
SERIALIZER_MAP = {
    "SentenceText": SentenceTextSerializer,
    "TranslationPair": TranslationPairSerializer,
    "OCRDocument": OCRDocumentSerializer,
    "BlockText": BlockTextSerializer,
    "Conversation": ConversationSerializer,
    "SpeechConversation": SpeechConversationSerializer,
    "PromptBase": PromptBaseSerializer,
    "PromptAnswer": PromptAnswerSerializer,
    "PromptAnswerEvaluation": PromptAnswerEvaluationSerializer,
    "Instruction": InstructionsSerializer,
    "Interaction": InteractionsSerializer,
}

# class CollectionDatasetSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CollectionDataset
#         fields = '__all__'

# class SpeechCollectionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SpeechCollection
#         fields = '__all__'

# class SpeechRecognitionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SpeechRecognition
#         fields = '__all__'

# class MonolingualSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Monolingual
#         fields = '__all__'

# class TranslationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Translation
#         fields = '__all__'

# class OCRSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OCR
#         fields = '__all__'

# class VideoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Video
#         fields = '__all__'

# class VideoChunkSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = VideoChunk
#         fields = '__all__'
