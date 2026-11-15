import ast
import gettext
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone, translation
from rest_framework.test import APITestCase

from apps.accounts.emails import send_verification_email
from apps.accounts.models import User
from apps.cv.manual_generation import MANUAL_CV_PLAN_LIMITS
from apps.jobs.models import DailyQuota, Job
from apps.jobs.scoring import score_job
from apps.notifications.models import PushSubscription
from apps.notifications.tasks import send_inactivity_notification_for_user, send_new_jobs_notification
from apps.profiles.models import Education, Profile

from .testing import LOCMEM_CACHES

PO_PATH = Path(settings.BASE_DIR) / "locale" / "en" / "LC_MESSAGES" / "django.po"
MO_PATH = PO_PATH.with_suffix(".mo")

VALID_LINKEDIN_URL = "https://www.linkedin.com/jobs/view/4012345678/"


def _parse_po(text):
    """Voci del .po come dict {msgid: {"flags", "msgid_plural", "msgstr": {indice: testo}}}."""
    entries = {}
    for block in text.strip().split("\n\n"):
        flags, fields, current = set(), {}, None
        for line in block.splitlines():
            if line.startswith("#~"):
                fields, current = {}, None
                break
            if line.startswith("#,"):
                flags.update(flag.strip() for flag in line[2:].split(","))
            elif line.startswith("#"):
                continue
            elif line.startswith('"'):
                fields[current] += ast.literal_eval(line)
            else:
                current, _sep, value = line.partition(" ")
                fields[current] = ast.literal_eval(value)
        if "msgid" not in fields:
            continue
        msgstr = {0: fields["msgstr"]} if "msgstr" in fields else {
            int(key[7:-1]): value for key, value in fields.items() if key.startswith("msgstr[")
        }
        entries[fields["msgid"]] = {
            "flags": flags, "msgid_plural": fields.get("msgid_plural"), "msgstr": msgstr,
        }
    return entries


class TranslationCatalogTests(TestCase):
    """Il catalogo inglese è completo e il .mo committato corrisponde al .po
    (Sprint 71): una voce nuova o cambiata senza traduzione, una traduzione
    proposta in automatico da makemessages (fuzzy) o un .mo non ricompilato
    fanno fallire la suite."""

    def setUp(self):
        self.entries = _parse_po(PO_PATH.read_text(encoding="utf-8"))

    def test_po_has_no_fuzzy_or_empty_entries(self):
        self.assertGreater(len(self.entries), 100)
        fuzzy = [msgid for msgid, entry in self.entries.items() if "fuzzy" in entry["flags"]]
        empty = [
            msgid for msgid, entry in self.entries.items()
            if msgid and (not entry["msgstr"] or not all(entry["msgstr"].values()))
        ]
        self.assertEqual(fuzzy, [])
        self.assertEqual(empty, [])

    def test_compiled_mo_matches_po(self):
        with MO_PATH.open("rb") as handle:
            catalog = dict(gettext.GNUTranslations(handle)._catalog)
        catalog.pop("", None)
        expected = {}
        for msgid, entry in self.entries.items():
            if not msgid:
                continue
            if entry["msgid_plural"] is None:
                expected[msgid] = entry["msgstr"][0]
            else:
                for index, value in entry["msgstr"].items():
                    expected[(msgid, index)] = value
        self.assertEqual(catalog, expected)


class _ApiLanguageMixin:
    def post(self, path, data=None, lang=None):
        headers = {"HTTP_ACCEPT_LANGUAGE": lang} if lang else {}
        return self.client.post(path, data or {}, format="json", **headers)


class ApiMessagesLanguageTests(_ApiLanguageMixin, APITestCase):
    def _user(self, email="i18n@example.com", **extra):
        return User.objects.create_user(username=email, email=email, password="pw-I18n-12345!", **extra)

    def test_wrong_login(self):
        self._user()
        data = {"email": "i18n@example.com", "password": "wrong-password"}
        self.assertEqual(
            self.post("/api/accounts/login/", data, "it").data["non_field_errors"], ["Credenziali non valide."]
        )
        self.assertEqual(
            self.post("/api/accounts/login/", data, "en").data["non_field_errors"], ["Invalid credentials."]
        )
        # Senza header o con una lingua non supportata: italiano, come prima.
        self.assertEqual(self.post("/api/accounts/login/", data).data["non_field_errors"], ["Credenziali non valide."])
        self.assertEqual(
            self.post("/api/accounts/login/", data, "fr-FR,fr;q=0.9").data["non_field_errors"],
            ["Credenziali non valide."],
        )
        self.assertEqual(
            self.post("/api/accounts/login/", data, "en-GB,en;q=0.9").data["non_field_errors"],
            ["Invalid credentials."],
        )

    @override_settings(REGISTRATION_INVITE_CODE="invito-giusto")
    def test_registration_with_wrong_invite_code(self):
        data = {
            "email": "new@example.com", "password": "pw-New-User-12345!", "invite_code": "sbagliato",
            "accept_privacy": True, "accept_terms": True, "confirm_age": True,
        }
        it = self.post("/api/accounts/register/", data, "it")
        en = self.post("/api/accounts/register/", data, "en")
        self.assertEqual(it.status_code, 400)
        self.assertEqual(it.data["invite_code"], ["Registrazione non consentita: codice di invito mancante o non valido."])
        self.assertEqual(en.data["invite_code"], ["Registration not allowed: invite code missing or invalid."])

    def test_cv_generation_quota_exhausted(self):
        user = self._user()
        profile = Profile.objects.create(user=user, city="Roma")
        Education.objects.create(profile=profile, institution="Uni", title="Laurea", end_date="2019-07-01")
        job = Job.objects.create(
            user=user, source=Job.Source.LINKEDIN, external_id="ext-i18n", title="PM",
            company="Acme", location="Roma", description="Descrizione.",
        )
        DailyQuota.objects.create(
            user=user, date=timezone.localtime(timezone.now()).date(),
            manual_cv_count=MANUAL_CV_PLAN_LIMITS[user.plan],
        )
        self.client.force_authenticate(user)
        it = self.post(f"/api/jobs/{job.pk}/generate-cv/", {}, "it")
        en = self.post(f"/api/jobs/{job.pk}/generate-cv/", {}, "en")
        self.assertEqual(it.status_code, 409)
        self.assertEqual(
            it.data["detail"],
            "Hai raggiunto il limite giornaliero di generazioni manuali e il saldo credito non è sufficiente.",
        )
        self.assertEqual(
            en.data["detail"],
            "You have reached the daily CV generation limit and your credit balance is not sufficient.",
        )

    def test_import_not_allowed_on_free_plan(self):
        self.client.force_authenticate(self._user(plan=User.Plan.FREE))
        it = self.post("/api/jobs/import/", {"url": VALID_LINKEDIN_URL}, "it")
        en = self.post("/api/jobs/import/", {"url": VALID_LINKEDIN_URL}, "en")
        self.assertEqual(it.status_code, 403)
        self.assertEqual(it.data["detail"], "L'import manuale di job è riservato al piano Pro.")
        self.assertEqual(en.data["detail"], "Manual job import is reserved for the Pro plan.")

    def test_manual_collection_already_used_today(self):
        # Sprint 77: una raccolta al giorno (automatica o manuale); senza
        # ricerche attive non si consuma la quota, quindi ne serve una.
        from apps.searches.models import SavedSearch

        user = self._user()
        SavedSearch.objects.create(user=user, keywords="PM", city="Roma", country="Italia", is_active=True)
        DailyQuota.objects.create(user=user, date=timezone.localtime(timezone.now()).date(), collection_count=1)
        self.client.force_authenticate(user)
        it = self.post("/api/jobs/collect/", None, "it")
        en = self.post("/api/jobs/collect/", None, "en")
        self.assertEqual(it.status_code, 409)
        self.assertEqual(it.data["detail"], "La raccolta di oggi è già stata fatta. Massimo 1 al giorno.")
        self.assertEqual(en.data["detail"], "Today's collection has already been done. At most 1 per day.")

    def test_length_validation(self):
        # Messaggio standard di DRF: tradotto dalle sue traduzioni (it/en).
        self.client.force_authenticate(self._user())
        data = {"objective_statement": "x" * 2001}
        it = self.client.patch("/api/accounts/me/", data, format="json", HTTP_ACCEPT_LANGUAGE="it")
        en = self.client.patch("/api/accounts/me/", data, format="json", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(it.status_code, 400)
        self.assertEqual(it.data["objective_statement"], ["Assicurati che questo campo non abbia più di 2000 caratteri."])
        self.assertEqual(en.data["objective_statement"], ["Ensure this field has no more than 2000 characters."])

    def test_own_validation_with_placeholder(self):
        self.client.force_authenticate(self._user())
        it = self.client.get("/api/jobs/?section=nope", HTTP_ACCEPT_LANGUAGE="it")
        en = self.client.get("/api/jobs/?section=nope", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(it.status_code, 400)
        self.assertTrue(it.data["detail"].startswith("Sezione non valida. Valori ammessi: "))
        self.assertTrue(en.data["detail"].startswith("Invalid section. Allowed values: "))

    @override_settings(LEGAL_GATE_ENABLED=True)
    def test_legal_gate(self):
        self.client.force_authenticate(self._user())
        it = self.client.get("/api/jobs/", HTTP_ACCEPT_LANGUAGE="it")
        en = self.client.get("/api/jobs/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(it.status_code, 403)
        self.assertEqual(en.data["code"], "legal_acceptance_required")
        self.assertEqual(it.data["detail"], "Per continuare devi accettare l'informativa privacy e i termini di servizio.")
        self.assertEqual(en.data["detail"], "To continue you must accept the privacy policy and the terms of service.")

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_throttling(self):
        from django.core.cache import cache

        cache.clear()
        data = {"email": "victim@example.com"}
        responses = [self.post("/api/accounts/password-reset/", data, "en") for _ in range(4)]
        cache.clear()
        # Senza email configurata l'endpoint risponde 503: il limite si
        # applica comunque, prima della view.
        self.assertEqual(responses[-1].status_code, 429)
        self.assertRegex(responses[-1].data["detail"], r"^Too many requests: please try again in \d+ (minutes?|hours?)\.$")
        responses = [self.post("/api/accounts/password-reset/", data, "it") for _ in range(4)]
        cache.clear()
        self.assertEqual(responses[-1].status_code, 429)
        self.assertRegex(responses[-1].data["detail"], r"^Troppe richieste: riprova tra \d+ (minut[oi]|or[ae])\.$")

    def test_admin_stays_italian(self):
        response = self.client.get(f"/{settings.DJANGO_ADMIN_PATH}login/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Nome utente")
        self.assertNotIn("Content-Language", response.headers)

    def test_language_does_not_leak_after_the_request(self):
        self._user()
        self.post("/api/accounts/login/", {"email": "i18n@example.com", "password": "x"}, "en")
        self.assertEqual(translation.get_language(), settings.LANGUAGE_CODE)


class BackgroundTextsLanguageTests(TestCase):
    """Fuori da una richiesta (task Celery) vale `User.interface_language`."""

    def _user(self, language):
        user = User.objects.create_user(
            username=f"bg-{language}@example.com", email=f"bg-{language}@example.com",
            password="pw-Bg-12345!", interface_language=language,
        )
        PushSubscription.objects.create(
            user=user, endpoint=f"https://push.example.com/{language}", p256dh_key="k", auth_key="a",
        )
        return user

    def _job(self, user, external_id="ext-bg"):
        return Job.objects.create(
            user=user, source=Job.Source.LINKEDIN, external_id=external_id, title="PM",
            company="Acme", location="Roma", description="Descrizione.",
        )

    def _new_jobs_payload(self, user):
        # Sprint 77: notifica a fine raccolta automatica (stessi testi della
        # vecchia notifica mattutina).
        with patch("apps.notifications.tasks.send_web_push") as mock_send:
            self.assertTrue(send_new_jobs_notification(user))
        return mock_send.call_args.args[1]

    def test_new_jobs_notification_payload(self):
        self.assertEqual(
            self._new_jobs_payload(self._user("it")),
            {"title": "Nuovi job pronti", "body": "Ci sono nuove offerte da valutare nella tua lista."},
        )
        # Anche con un'altra lingua attiva sul thread (es. dopo una richiesta).
        with translation.override("it"):
            payload = self._new_jobs_payload(self._user("en"))
        self.assertEqual(payload, {"title": "New jobs ready", "body": "There are new job offers to review in your list."})

    def test_inactivity_notification_payload(self):
        user = self._user("en")
        User.objects.filter(pk=user.pk).update(last_activity_reset=timezone.now() - timedelta(days=8))
        user.refresh_from_db()
        with patch("apps.notifications.tasks.send_web_push") as mock_send:
            self.assertTrue(send_inactivity_notification_for_user(user))
        self.assertEqual(mock_send.call_args.args[1]["title"], "You haven't applied in a while")

    def test_language_cap_prefix_in_owner_language(self):
        result = {
            "score": 9, "score_match": [], "score_gaps": [], "score_reasoning": "Testo del modello.",
            "language_check": {"required": True, "language": "German", "international_exception": False},
        }
        jobs = {lang: self._job(self._user(lang), f"ext-cap-{lang}") for lang in ("it", "en")}
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=result), translation.override("it"):
            for job in jobs.values():
                score_job(job)
        for job in jobs.values():
            job.refresh_from_db()
            self.assertEqual(job.score, 3)
        self.assertEqual(
            jobs["it"].score_reasoning,
            "Punteggio limitato a 3/10: lingua richiesta (German) assente dal profilo. Testo del modello.",
        )
        self.assertEqual(
            jobs["en"].score_reasoning,
            "Score capped at 3/10: required language (German) missing from the profile. Testo del modello.",
        )

    @override_settings(
        EMAIL_HOST_USER="sender@example.com", EMAIL_HOST_PASSWORD="app-password",
        DEFAULT_FROM_EMAIL="sender@example.com",
    )
    def test_service_email_keeps_its_texts(self):
        # Le email dello Sprint 67 ora passano da gettext: stessi testi di prima.
        for language, subject, opening in [
            ("it", "App-apply — Conferma il tuo indirizzo email", "per completare la registrazione ad App-apply"),
            ("en", "App-apply — Confirm your email address", "to complete your App-apply registration"),
        ]:
            mail.outbox.clear()
            user = User.objects.create_user(
                username=f"mail-{language}@example.com", email=f"mail-{language}@example.com",
                password="pw-Mail-12345!", interface_language=language,
            )
            with translation.override("en" if language == "it" else "it"):
                send_verification_email(user)
            self.assertEqual(mail.outbox[0].subject, subject)
            self.assertIn(opening, mail.outbox[0].body)
            self.assertTrue(mail.outbox[0].body.endswith(
                "— App-apply\nEmail automatica: non rispondere a questo messaggio." if language == "it"
                else "— App-apply\nAutomated email: please do not reply to this message."
            ))
