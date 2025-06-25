from rest_framework import serializers


class SelectionSerializer(serializers.Serializer):
    keystrokes = serializers.CharField()
    results = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    opted = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class TransliterationSerializer(serializers.Serializer):
    word = serializers.CharField()
    language = serializers.CharField()
    steps = SelectionSerializer(many=True)

class VoiceLogsSerializer(serializers.Serializer):
    audioBase64 = serializers.CharField()
    machineTranscription = serializers.CharField()
    correctedTranscription = serializers.CharField()
    timestamp = serializers.DateTimeField()

class TranscriptionSerializer(serializers.Serializer):
    platform = serializers.CharField()
    user_email = serializers.CharField()
    language = serializers.CharField()
    script = serializers.IntegerField()
    task_id = serializers.IntegerField()
    voiceLogs = VoiceLogsSerializer(many=True)