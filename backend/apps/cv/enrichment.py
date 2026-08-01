from apps.profiles.models import Experience

from .manual_generation import request_manual_cv_generation


class EnrichmentExperienceNotFound(Exception):
    """L'esperienza indicata non esiste o non appartiene al profilo
    dell'utente (Docs/03 §5.6): l'arricchimento non può mai introdurre
    un'azienda/ruolo del tutto assente dal profilo master."""


def _format_enrichment_text(experience, additional_bullets):
    """Testo passato al servizio di generazione come contesto aggiuntivo
    (finisce anche in `CVDocument.enrichment_used`, Sprint 10): inquadra
    l'aggiunta come attività reale dell'esperienza esistente, non come
    un'esperienza a sé."""
    header = f"{experience.role} presso {experience.company}".strip()
    bullets_text = "; ".join(bullet for bullet in additional_bullets if bullet)
    return f"{header}. Attività aggiuntive: {bullets_text}".strip()


def generate_cv_with_enrichment(job, experience_id, additional_bullets, save_to_profile=False):
    """Applica un arricchimento agganciato a un'esperienza esistente prima
    di una generazione/rigenerazione manuale (Docs/03 §5.6): il dettaglio è
    sempre usato come contesto per questa generazione (con priorità massima
    di inclusione — vedi `generation.py`); se `save_to_profile` è vero, i
    nuovi bullet sono anche accodati all'`Experience` esistente nel profilo
    master (persistenti, riusabili nei CV futuri, ma senza più priorità in
    quel caso — §5.6)."""
    try:
        experience = Experience.objects.get(pk=experience_id, profile__user=job.user)
    except Experience.DoesNotExist as exc:
        raise EnrichmentExperienceNotFound(
            "L'esperienza indicata non esiste nel tuo profilo."
        ) from exc

    enrichment_text = _format_enrichment_text(experience, additional_bullets)

    if save_to_profile:
        experience.bullets = [*experience.bullets, *additional_bullets]
        experience.save(update_fields=["bullets"])

    return request_manual_cv_generation(
        job,
        enrichment=enrichment_text,
        protected_bullets=additional_bullets,
        protected_experience_id=experience.pk,
    )
