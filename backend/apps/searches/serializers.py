from rest_framework import serializers

from .models import SavedSearch


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ["id", "keywords", "city", "country", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]
