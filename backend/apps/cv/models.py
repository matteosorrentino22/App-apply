from django.conf import settings
from django.db import models

from apps.jobs.models import Job


class CVDocument(models.Model):
    class GenerationType(models.TextChoices):
        AUTOMATIC = "automatic", "Automatica"
        MANUAL = "manual", "Manuale"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="cv_documents")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_documents"
    )
    html_source = models.TextField()
    pdf_file = models.FileField(upload_to="cv_documents/")
    generated_at = models.DateTimeField(auto_now_add=True)
    generation_type = models.CharField(max_length=10, choices=GenerationType.choices)
    # Testo "gap da colmare + istruzioni" usato per questa generazione
    # (Sprint 44, apps.cv.gap_filling) — prima era il testo dell'arricchimento
    # manuale su un'esperienza scelta dall'utente, funzione ora rimossa.
    extra_instructions_used = models.TextField(blank=True, default="")
    # Riferimento interno di provenienza per ogni Area of Expertise prodotta
    # (Docs/03 §5.3, §13): mai mostrato all'utente, serve solo alla diagnosi
    # in fase di tuning del prompt (verificare che le aree siano riconducibili
    # a contenuto reale del profilo). Dato di servizio, non una nuova tabella.
    areas_of_expertise_grounding = models.JSONField(default=list, blank=True)
    # Snapshot strutturato del contenuto (Sprint 51, editor CV): prima si
    # salvava solo l'HTML finale, mai la struttura — senza questo campo non
    # si potrebbe riaprire un CV già generato (automatico o manuale) in
    # `CVDraft` per modificarlo. Vuoto (`{}`) per i CVDocument creati prima
    # di questo campo. Vedi `apps.cv.draft` per la forma esatta.
    content_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"CV — {self.job} ({self.generated_at})"


class CVDraft(models.Model):
    """Copia di lavoro, modificabile, del contenuto strutturato di un CV
    (Sprint 51): a differenza di `CVDocument`, non ha mai un PDF proprio —
    serve solo come stato intermedio tra "generato dall'AI" e "PDF finale".
    Un solo draft "corrente" per job (non uno storico): aprire di nuovo
    l'editor o generare un nuovo CV sovrascrive il draft esistente, non lo
    duplica. Il PDF finale nasce da `apps.cv.draft.finalize_cv_draft`, che
    riusa la stessa pipeline di rendering di `generate_cv` ma senza
    richiamare Claude né il taglio automatico al budget — qui le scelte sono
    già quelle dell'utente."""

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="cv_draft")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_drafts"
    )
    content_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Draft CV — {self.job} ({self.updated_at})"


class CoverLetterDocument(models.Model):
    """Mirror di CVDocument (Sprint 42): artefatto indipendente, mai generato
    automaticamente, sempre su richiesta esplicita dell'utente per un job."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="cover_letter_documents")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cover_letter_documents"
    )
    html_source = models.TextField()
    pdf_file = models.FileField(upload_to="cover_letter_documents/")
    generated_at = models.DateTimeField(auto_now_add=True)
    # Testo libero fornito dall'utente in questa generazione (indicazioni di
    # tono/enfasi e/o dettagli reali non ancora nel profilo, sotto la sua
    # responsabilità di veridicità — stesso principio dell'arricchimento
    # CV): alimenta anche il menu "indicazioni precedenti" nel popup di
    # generazione, tra tutti i job dell'utente.
    instructions_used = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Cover letter — {self.job} ({self.generated_at})"


class ReferralMessageDocument(models.Model):
    """Messaggio di networking (LinkedIn o email) con cui il candidato
    chiede a qualcuno di essere raccomandato/presentato per un job (Sprint
    50). A differenza di CV/cover letter non produce un PDF: è testo da
    copiare nel client dell'utente (LinkedIn, email), non un documento da
    allegare a una candidatura. A differenza della cover letter, più
    messaggi hanno senso sullo stesso job (destinatari diversi: un contatto
    interno, il recruiter, l'hiring manager): nessun concetto di "ultimo"
    che sostituisce i precedenti, la UI mostra lo storico per job."""

    class Channel(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"
        EMAIL = "email", "Email"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="referral_message_documents")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_message_documents"
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    recipient_name = models.CharField(max_length=255, blank=True, default="")
    # Salvato ma non ancora usato per personalizzare il messaggio: leggere
    # il contenuto di un profilo LinkedIn richiederebbe un nuovo scraping
    # dedicato (nessun meccanismo del genere esiste oggi, a differenza delle
    # offerte di lavoro via Apify) — previsto per un prossimo rilascio, per
    # ora solo un riferimento comodo per l'utente.
    recipient_linkedin_url = models.URLField(max_length=500, blank=True, default="")
    # Stesso principio di CoverLetterDocument.instructions_used: testo
    # libero fornito dall'utente, alimenta anche il menu "indicazioni
    # precedenti" nel popup di generazione.
    instructions_used = models.TextField(blank=True, default="")
    # Vuoto per canale "linkedin" (nessun oggetto per un messaggio diretto).
    subject = models.CharField(max_length=255, blank=True, default="")
    content = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Messaggio di networking — {self.job} ({self.generated_at})"
