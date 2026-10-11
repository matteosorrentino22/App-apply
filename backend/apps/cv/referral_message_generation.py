from .models import ReferralMessageDocument
from .referral_message_content import generate_referral_message_content


def generate_referral_message(
    job, channel, recipient_name="", recipient_linkedin_url="", instructions=""
):
    """Genera un messaggio di networking per `job` sul profilo del suo
    utente (Sprint 50): a differenza di CV/cover letter nessun rendering
    HTML/PDF — il contenuto generato da Claude è già il testo finale da
    copiare nel client dell'utente.

    Solleva l'eccezione a chi chiama in caso di fallimento (chiamata
    Claude): la gestione (guardia di concorrenza, quota/credito, RunLog) è
    responsabilità di chi orchestra la generazione, stesso principio di
    `cover_letter_generation.generate_cover_letter`."""
    user = job.user
    profile = user.profile

    content = generate_referral_message_content(
        profile, job, user.cv_language_mode, channel, recipient_name, instructions
    )

    return ReferralMessageDocument.objects.create(
        job=job,
        user=user,
        channel=channel,
        recipient_name=recipient_name,
        recipient_linkedin_url=recipient_linkedin_url,
        instructions_used=instructions,
        subject=content["subject"],
        content=content["message"],
    )
