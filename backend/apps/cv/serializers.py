from rest_framework import serializers


class CvEnrichmentSerializer(serializers.Serializer):
    """Dettaglio di esperienza reale non ancora nel profilo master, da usare
    per una generazione/rigenerazione manuale (01-specifiche-funzionali-v4.md
    §4.8). Stessi campi di `apps.profiles.models.Experience`, così il
    dettaglio è salvabile tale e quale nel profilo se `save_to_profile=True`.
    """

    company = serializers.CharField(max_length=255)
    role = serializers.CharField(max_length=255)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    start_date = serializers.DateField(required=False, allow_null=True, default=None)
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    bullets = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False, default=list
    )
    technologies = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False, default=list
    )
    save_to_profile = serializers.BooleanField(required=False, default=False)
