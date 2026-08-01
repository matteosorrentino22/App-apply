from rest_framework import serializers


class CvEnrichmentSerializer(serializers.Serializer):
    """Dettaglio di arricchimento agganciato a un'esperienza **già presente**
    nel profilo master (Docs/03 §5.6 — sostituisce §4.8 di
    01-specifiche-funzionali-v5.md): non introduce mai un'azienda/ruolo del
    tutto nuovo, solo attività/progetti aggiuntivi su un'esperienza esistente.
    """

    experience_id = serializers.IntegerField()
    additional_bullets = serializers.ListField(
        child=serializers.CharField(allow_blank=False), min_length=1
    )
    save_to_profile = serializers.BooleanField(required=False, default=False)
