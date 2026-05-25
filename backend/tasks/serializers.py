from dataclasses import fields
from rest_framework import serializers
from tasks.models import Task, Annotation, Prediction
from tasks.redaction import convert_model_names_to_ids

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        convert_model_names_to_ids(rep)
        return rep


class AnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = "__all__"


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = "__all__"


class NestedAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ("id", "result")


class TaskAnnotationSerializer(serializers.ModelSerializer):
    correct_annotation = NestedAnnotationSerializer()

    class Meta:
        model = Task
        fields = "__all__"
