from django.conf import settings
from django.db import models

from apps.common.files import cover_letter_document_upload_to, cv_document_upload_to
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
    pdf_file = models.FileField(upload_to=cv_document_upload_to)
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
    # Pagine del PDF prodotto (Sprint 69): l'obiettivo è 1 pagina, ma il caso
    # residuale multi-pagina è accettato (Docs/03 §6) e va segnalato
    # all'utente. Nullo per i documenti precedenti.
    page_count = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"CV — {self.job} ({self.generated_at})"


class CVDraft(models.Model):
    """Copia di lavoro, modificabile, del contenuto strutturato di un CV
    (Sprint 51): non ha mai un PDF proprio. Una sola bozza per job, seminata
    dall'ultimo `CVDocument`. Generare un nuovo CV non la tocca: quando
    l'ultimo documento è diverso da `source_document`, l'editor chiede se
    ripartire dal nuovo documento (bozza e chat riseminate) o continuare la
    bozza (Sprint 69). Il PDF finale nasce da
    `apps.cv.draft.finalize_cv_draft`, con lo stesso template ma senza
    Claude né taglio automatico."""

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="cv_draft")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_drafts"
    )
    content_json = models.JSONField(default=dict, blank=True)
    # Cronologia della chat di assistenza (Sprint 59): lista di turni
    # `{"role": "user"|"assistant", "message": str, "actions": [...]}` (solo
    # per "assistant", le modifiche proposte in quel turno, con lo stato di
    # accettazione/rifiuto scelto dall'utente) — persistita così la
    # conversazione non si perde ricaricando la pagina, a differenza della
    # preview che è sempre ricalcolata al volo.
    chat_history = models.JSONField(default=list, blank=True)
    # Documento di riferimento della bozza (Sprint 69): quello da cui è stata
    # seminata, poi quello prodotto dalla sua finalizzazione o quello che
    # l'utente ha scelto di ignorare ("continua la bozza"). Se l'ultimo
    # CVDocument del job è un altro, la bozza è "superata".
    source_document = models.ForeignKey(
        CVDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
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
    pdf_file = models.FileField(upload_to=cover_letter_document_upload_to)
    generated_at = models.DateTimeField(auto_now_add=True)
    # Testo libero fornito dall'utente in questa generazione (indicazioni di
    # tono/enfasi e/o dettagli reali non ancora nel profilo, sotto la sua
    # responsabilità di veridicità — stesso principio dell'arricchimento
    # CV): alimenta anche il menu "indicazioni precedenti" nel popup di
    # generazione, tra tutti i job dell'utente.
    instructions_used = models.TextField(blank=True, default="")
    # Snapshot strutturato del contenuto (Sprint 63, editor cover letter):
    # stesso principio di CVDocument.content_json — senza questo non si
    # potrebbe riaprire una lettera già generata in CoverLetterDraft per
    # modificarla. Vuoto (`{}`) per le lettere generate prima di questo
    # campo. Vedi `apps.cv.cover_letter_draft` per la forma esatta.
    content_json = models.JSONField(default=dict, blank=True)
    page_count = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Cover letter — {self.job} ({self.generated_at})"


class CoverLetterDraft(models.Model):
    """Mirror di CVDraft (Sprint 63): copia di lavoro modificabile dei
    paragrafi di una cover letter, seminata dall'ultima
    `CoverLetterDocument`. Una nuova generazione non la tocca: come per il
    CV, l'editor chiede se riseminarla quando l'ultimo documento è diverso
    da `source_document` (Sprint 69)."""

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="cover_letter_draft")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cover_letter_drafts"
    )
    content_json = models.JSONField(default=dict, blank=True)
    chat_history = models.JSONField(default=list, blank=True)
    source_document = models.ForeignKey(
        CoverLetterDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Draft cover letter — {self.job} ({self.updated_at})"


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
    # Salvato ma non usato per scrivere il messaggio (né passato al prompt):
    # leggere un profilo LinkedIn richiederebbe uno scraping dedicato, previsto
    # per un rilascio futuro. Oggi è solo un riferimento per l'utente, mostrato
    # nello storico dei messaggi (Sprint 69).
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
