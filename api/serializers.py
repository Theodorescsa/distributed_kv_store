from rest_framework import serializers

class KeyValueSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=255)