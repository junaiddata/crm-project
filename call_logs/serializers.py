from rest_framework import serializers
from .models import CallLog


class CallLogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CallLog
        fields = ['caller_number', 'received_by', 'sim', 'direction', 'status', 'duration']

    def validate_status(self, value):
        if value not in ['answered', 'missed', 'rejected']:
            raise serializers.ValidationError("status must be: answered, missed, or rejected")
        return value

    def validate_direction(self, value):
        if value not in ['incoming', 'outgoing']:
            raise serializers.ValidationError("direction must be: incoming or outgoing")
        return value


class CallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CallLog
        fields = ['id', 'caller_number', 'received_by', 'sim', 'direction', 'status', 'duration', 'timestamp']
