from apps.profiles.models import Experience

from .manual_generation import request_manual_cv_generation


def _format_enrichment_text(detail):
    """Testo libero passato al servizio di generazione come contesto
    aggiuntivo (§6.2 tecniche: la stessa stringa finisce anche in
    `CVDocument.enrichment_used`, Sprint 10)."""
    header = f"{detail['role']} presso {detail['company']}".strip()
    bullets_text = "; ".join(bullet for bullet in detail.get("bullets", []) if bullet)
    return f"{header}. {bullets_text}".strip(". ") if bullets_text else header


def generate_cv_with_enrichment(job, detail, save_to_profile=False):
    """Applica un dettaglio di arricchimento prima di una generazione/
    rigenerazione manuale (01-specifiche-funzionali-v4.md §4.8): il dettaglio
    è sempre usato come contesto per questa generazione; se
    `save_to_profile` è vero, viene anche salvato come `Experience` del
    profilo master (persistente, riusabile in generazioni future) — altrimenti
    resta valido solo per questo CV, il profilo master non cambia."""
    enrichment_text = _format_enrichment_text(detail)

    if save_to_profile:
        Experience.objects.create(
            profile=job.user.profile,
            company=detail["company"],
            role=detail["role"],
            location=detail.get("location", ""),
            start_date=detail.get("start_date"),
            end_date=detail.get("end_date"),
            bullets=detail.get("bullets", []),
            technologies=detail.get("technologies", []),
        )

    return request_manual_cv_generation(job, enrichment=enrichment_text)
