from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        
class NotificationSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "notification_type", "on_click", "created_at", "priority", "seen_json"]
