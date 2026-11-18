# Cancellazione ed export dei dati di un account (Sprint 67, GDPR artt. 17 e 20).
import json
import logging
import os
import tempfile
import zipfile

from django.core.files.storage import default_storage
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from apps.cv.models import CoverLetterDocument, CoverLetterDraft, CVDocument, CVDraft, ReferralMessageDocument
from apps.jobs.models import DailyQuota, Job, JobFilterPreset, RunLog
from apps.notifications.models import PushSubscription
from apps.profiles.models import Certification, Education, Experience, Language, Profile, Skill
from apps.searches.models import JobWish, SavedSearch

from .models import AuthToken, LegalAcceptance

logger = logging.getLogger(__name__)


def delete_account(user):
    """Elimina l'utente e, a cascata, profilo, ricerche, job, documenti,
    bozze e chat, preset, quote, token, sottoscrizioni push e accettazioni.
    I file su disco (PDF, foto) e il testo dei RunLog, che restano senza
    utente per le statistiche tecniche, li puliscono i segnali di
    apps.accounts.signals: valgono anche per una cancellazione dall'admin."""
    with transaction.atomic():
        user.delete()


def _rows(queryset, exclude=()):
    return [{k: v for k, v in row.items() if k not in exclude} for row in queryset.values()]


README = """App-apply — esportazione dei tuoi dati / your data export

IT
- dati.json: tutti i dati del tuo account in formato JSON (account, accettazioni
  di informativa e termini, profilo e sezioni, ricerche salvate, lavoro dei desideri, offerte con
  punteggi e motivazioni, documenti generati con il loro contenuto, bozze e
  cronologie delle chat, messaggi di networking, filtri salvati, quote
  giornaliere, sessioni attive, sottoscrizioni alle notifiche, registri delle
  elaborazioni). La password non è inclusa (è conservata solo come hash).
- files/: i PDF dei CV e delle cover letter generati e la foto del profilo.
  Il campo "file" in dati.json indica il percorso del file in questo archivio.

EN
- dati.json: all your account data in JSON format (account, privacy policy and
  terms acceptances, profile and sections, saved searches, dream job, jobs with scores and
  reasons, generated documents with their content, drafts and chat histories,
  networking messages, saved filters, daily quotas, active sessions, push
  subscriptions, processing logs). The password is not included (it is only
  stored as a hash).
- files/: the generated CV and cover letter PDFs and your profile photo.
  The "file" field in dati.json is the path of the file in this archive.
"""


def build_export(user):
    """Restituisce un file temporaneo (posizionato all'inizio) con lo ZIP
    dell'export, generato in modo sincrono."""
    files = []

    def add_file(field_name, archive_name):
        if field_name:
            files.append((field_name, archive_name))
            return archive_name
        return None

    account = {
        field: getattr(user, field)
        for field in [
            "id", "email", "first_name", "last_name", "date_joined", "last_login", "created_at",
            "plan", "extra_credit", "timezone", "interface_language", "cv_language_mode",
            "cv_include_photo", "objective_statement", "email_verified", "notifications_enabled",
            "last_activity_reset", "last_notified_at", "last_inactivity_notified_at",
            # Raccolta automatica (Sprint 77).
            "auto_collection_enabled", "auto_collection_time", "auto_collection_last_local_date",
        ]
    }

    profile = Profile.objects.filter(user=user).first()
    profile_data = None
    if profile is not None:
        profile_data = _rows(Profile.objects.filter(pk=profile.pk), exclude=("photo", "user_id"))[0]
        if profile.photo:
            extension = os.path.splitext(profile.photo.name)[1]
            profile_data["photo_file"] = add_file(profile.photo.name, f"files/foto{extension}")
        profile_data["experiences"] = _rows(Experience.objects.filter(profile=profile), exclude=("profile_id",))
        profile_data["educations"] = _rows(Education.objects.filter(profile=profile), exclude=("profile_id",))
        profile_data["skills"] = _rows(Skill.objects.filter(profile=profile), exclude=("profile_id",))
        profile_data["certifications"] = _rows(
            Certification.objects.filter(profile=profile), exclude=("profile_id",)
        )
        profile_data["languages"] = _rows(Language.objects.filter(profile=profile), exclude=("profile_id",))

    cv_documents = []
    for row in _rows(CVDocument.objects.filter(user=user).order_by("id"), exclude=("user_id", "html_source")):
        row["file"] = add_file(row.pop("pdf_file"), f"files/cv/cv_job{row['job_id']}_{row['id']}.pdf")
        cv_documents.append(row)
    cover_letters = []
    for row in _rows(
        CoverLetterDocument.objects.filter(user=user).order_by("id"), exclude=("user_id", "html_source")
    ):
        row["file"] = add_file(
            row.pop("pdf_file"), f"files/cover_letter/cover_letter_job{row['job_id']}_{row['id']}.pdf"
        )
        cover_letters.append(row)

    data = {
        "exported_at": timezone.now(),
        "account": account,
        "legal_acceptances": _rows(LegalAcceptance.objects.filter(user=user), exclude=("user_id",)),
        "profile": profile_data,
        "saved_searches": _rows(SavedSearch.objects.filter(user=user).order_by("id"), exclude=("user_id",)),
        # Sprint 84: lavoro dei desideri (descrizione, paese, città e le
        # keyword ricavate dall'AI, che l'app non mostra ma sono dati
        # dell'utente: diritto di accesso).
        "job_wish": _rows(JobWish.objects.filter(user=user), exclude=("user_id",)),
        "jobs": _rows(Job.objects.filter(user=user).order_by("id"), exclude=("user_id",)),
        "cv_documents": cv_documents,
        "cv_drafts": _rows(CVDraft.objects.filter(user=user).order_by("id"), exclude=("user_id",)),
        "cover_letter_documents": cover_letters,
        "cover_letter_drafts": _rows(CoverLetterDraft.objects.filter(user=user).order_by("id"), exclude=("user_id",)),
        "referral_messages": _rows(
            ReferralMessageDocument.objects.filter(user=user).order_by("id"), exclude=("user_id",)
        ),
        "job_filter_presets": _rows(JobFilterPreset.objects.filter(user=user).order_by("id"), exclude=("user_id",)),
        "daily_quotas": _rows(DailyQuota.objects.filter(user=user).order_by("date"), exclude=("user_id",)),
        "sessions": _rows(AuthToken.objects.filter(user=user).order_by("id"), exclude=("user_id", "key_hash")),
        "push_subscriptions": _rows(
            PushSubscription.objects.filter(user=user).order_by("id"), exclude=("user_id", "p256dh_key", "auth_key")
        ),
        "run_logs": _rows(RunLog.objects.filter(user=user).order_by("id"), exclude=("user_id",)),
    }

    output = tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", README)
        archive.writestr(
            "dati.json", json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
        )
        for field_name, archive_name in files:
            try:
                with default_storage.open(field_name, "rb") as handle:
                    archive.writestr(archive_name, handle.read())
            except OSError:
                logger.warning("Export: file mancante (%s)", os.path.basename(field_name))
    output.seek(0)
    return output
