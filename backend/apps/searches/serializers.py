from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.accounts.models import User

from .models import MAX_CITIES_PER_SEARCH, SavedSearch


class SavedSearchSerializer(serializers.ModelSerializer):
    """Sprint 84 (A17, A18): paese + 1–5 città (Free 1, Pro 5) e modalità di
    lavoro (solo Pro). `city` resta accettato in scrittura per compatibilità
    (diventa la lista con quella sola città) e in lettura (la prima città)."""

    cities = serializers.ListField(child=serializers.CharField(max_length=255, allow_blank=True), required=False)
    city = serializers.CharField(max_length=255, required=False, write_only=True)

    class Meta:
        model = SavedSearch
        fields = ["id", "search_type", "keywords", "country", "cities", "city", "work_mode", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["city"] = instance.city
        return data

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def validate(self, attrs):
        legacy_city = attrs.pop("city", None)
        if "cities" not in attrs and legacy_city is not None:
            attrs["cities"] = [legacy_city]
        if self.instance is None and "cities" not in attrs:
            raise serializers.ValidationError({"cities": [_("Scegli almeno una città.")]})
        user = self._user()
        plan = getattr(user, "plan", User.Plan.FREE)
        if "cities" in attrs:
            cities = []
            for city in attrs["cities"]:
                city = city.strip()
                if city and city.casefold() not in {c.casefold() for c in cities}:
                    cities.append(city)
            limit = MAX_CITIES_PER_SEARCH[plan]
            if not cities:
                raise serializers.ValidationError({"cities": [_("Scegli almeno una città.")]})
            if len(cities) > limit:
                raise serializers.ValidationError(
                    {"cities": [_("Con il tuo piano una ricerca può avere al massimo %(max)s città.") % {"max": limit}]}
                )
            attrs["cities"] = cities
        if attrs.get("work_mode") and plan != User.Plan.PRO:
            raise serializers.ValidationError({"work_mode": [_("Scegliere remoto, ibrido o in sede è incluso nel piano Pro.")]})
        return attrs


class JobWishSerializer(serializers.Serializer):
    """Lavoro dei desideri (Sprint 84, A19): le keyword ricavate dall'AI non
    escono mai."""

    description = serializers.CharField(max_length=1000, allow_blank=True)
    country = serializers.CharField(max_length=255, allow_blank=True)
    cities = serializers.ListField(child=serializers.CharField(max_length=255, allow_blank=True), max_length=5)
    is_active = serializers.BooleanField()
