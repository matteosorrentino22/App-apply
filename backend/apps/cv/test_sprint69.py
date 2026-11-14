# Test dello Sprint 69: stati del job e generazione, annullamento della
# candidatura, numerazione dei gap, riseminatura delle bozze, finalizzazione
# con il contenuto corrente, id stabili e azioni della chat, contesto della
# chat con le decisioni, prezzo/saldo della chat, storico delle indicazioni,
# flag di generazione stantii, grassetto nei campi del CV.
import copy
import json
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.jobs.models import Job, RunLog
from apps.profiles.models import Education, Profile, Skill

from .cover_letter_draft_chat import _build_user_content as build_cover_letter_chat_content
from .cover_letter_manual_generation import (
    CoverLetterGenerationRejected,
    get_recent_instructions as get_recent_cover_letter_instructions,
    request_cover_letter_generation,
)
from .draft import render_context_from_draft
from .draft_chat import _build_user_content as build_cv_chat_content
from .gap_filling import build_extra_instructions, resolve_selected_gaps
from .manual_generation import ManualGenerationFailed, request_manual_cv_generation
from .models import (
    CoverLetterDocument,
    CoverLetterDraft,
    CVDocument,
    CVDraft,
    ReferralMessageDocument,
)
from .referral_message_manual_generation import (
    get_recent_instructions as get_recent_referral_instructions,
)
from .rendering import render_cv

User = get_user_model()


def _cv_content(summary="Sommario", bullets=None, with_ids=True):
    bullets = bullets or ["Guidato un team.", "Ridotto i costi."]
    return {
        "summary": summary,
        "qualification": "Project Manager",
        "translated_city": "Roma",
        "content_language": "it",
        "areas_of_expertise": ["Pianificazione", "Budget"],
        "experiences": [
            {
                "profile_experience_id": 7,
                "company": "Acme",
                "role": "PM",
                "location": "Roma, IT",
                "dates": "2020 - 2024",
                "technologies": [],
                "shown": True,
                "bullets": [
                    ({"id": f"b{i}", "text": text, "shown": True} if with_ids else {"text": text, "shown": True})
                    for i, text in enumerate(bullets)
                ],
            }
        ],
        "educations": [{"institution": "Uni", "title": "Laurea", "location": "", "dates": "2019", "notes": ""}],
        "skills": ["Scrum"],
        "certifications": [],
        "languages": [{"language": "it", "level": "mother_tongue"}],
    }


def _cover_letter_content(paragraphs=("Apertura.", "Esperienza.", "Chiusura.")):
    return {
        "content_language": "it",
        "translated_city": "Roma",
        "paragraphs": [{"id": f"p{i}", "text": text} for i, text in enumerate(paragraphs)],
    }


class _Base(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="s69@example.com", email="s69@example.com", password="pw-S69-12345!",
            extra_credit=Decimal("1.00"),
        )
        self.profile = Profile.objects.create(user=self.user, city="Roma")
        Education.objects.create(profile=self.profile, institution="Uni", title="Laurea", end_date="2019-07-01")
        Skill.objects.create(profile=self.profile, name="Scrum")
        self.client.force_authenticate(self.user)
        self.job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-s69",
            title="PM",
            company="Acme",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            score_gaps=[
                {"label": "Kubernetes", "reason": "richiesto"},
                {"label": "Inglese C1", "reason": ""},
                {"label": "SAFe", "reason": "certificazione"},
            ],
        )

    def _cv_document(self, content=None, page_count=1):
        return CVDocument.objects.create(
            job=self.job,
            user=self.user,
            html_source="<html></html>",
            generation_type=CVDocument.GenerationType.MANUAL,
            content_json=content if content is not None else _cv_content(),
            page_count=page_count,
        )

    def _cover_letter_document(self, content=None, instructions=""):
        return CoverLetterDocument.objects.create(
            job=self.job,
            user=self.user,
            html_source="<html></html>",
            content_json=content if content is not None else _cover_letter_content(),
            instructions_used=instructions,
        )

    def _detail(self):
        return self.client.get(f"/api/jobs/{self.job.pk}/").json()


class JobStatusAndGenerationTests(_Base):
    def test_successful_regeneration_keeps_application_done(self):
        self.job.status = Job.Status.APPLICATION_DONE
        self.job.save(update_fields=["status"])
        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(self.job)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.APPLICATION_DONE)
        self.assertIsNotNone(self.job.date_cv_generated)
        self.assertFalse(self.job.cv_generation_in_progress)

    def test_failed_generation_leaves_previous_status(self):
        for previous in (Job.Status.CV_GENERATED, Job.Status.APPLICATION_DONE):
            self.job.status = previous
            self.job.save(update_fields=["status"])
            with patch("apps.cv.manual_generation.generate_cv", side_effect=RuntimeError("boom")):
                with self.assertRaises(ManualGenerationFailed):
                    request_manual_cv_generation(self.job)
            self.job.refresh_from_db()
            self.assertEqual(self.job.status, previous)
            self.assertFalse(self.job.cv_generation_in_progress)
            self.assertIsNone(self.job.cv_generation_started_at)

    def test_system_exit_refunds_and_clears_flag_then_propagates(self):
        self.user.extra_credit = Decimal("0")
        self.user.save(update_fields=["extra_credit"])
        with patch("apps.cv.manual_generation.generate_cv", side_effect=SystemExit(1)):
            with self.assertRaises(SystemExit):
                request_manual_cv_generation(self.job)
        self.job.refresh_from_db()
        self.assertFalse(self.job.cv_generation_in_progress)
        self.assertEqual(self.user.daily_quotas.get().manual_cv_count, 0)
        self.assertTrue(RunLog.objects.filter(job=self.job, status=RunLog.Status.FAILURE).exists())

    def test_stale_flag_no_longer_blocks_generation(self):
        self.user.plan = User.Plan.PRO
        self.user.save(update_fields=["plan"])
        cases = [
            (timezone.now() - timedelta(minutes=40), True),
            (None, True),
            (timezone.now() - timedelta(minutes=5), False),
        ]
        for started_at, should_run in cases:
            Job.objects.filter(pk=self.job.pk).update(
                cover_letter_generation_in_progress=True, cover_letter_generation_started_at=started_at
            )
            with patch("apps.cv.cover_letter_manual_generation.generate_cover_letter") as mock_generate:
                if should_run:
                    request_cover_letter_generation(self.job)
                    mock_generate.assert_called_once()
                else:
                    with self.assertRaises(CoverLetterGenerationRejected):
                        request_cover_letter_generation(self.job)
                    mock_generate.assert_not_called()

    def test_serializer_hides_stale_flags_and_exposes_referral_flag(self):
        Job.objects.filter(pk=self.job.pk).update(
            cv_generation_in_progress=True,
            cv_generation_started_at=timezone.now() - timedelta(hours=1),
            referral_message_generation_in_progress=True,
            referral_message_generation_started_at=timezone.now(),
        )
        detail = self._detail()
        self.assertFalse(detail["cv_generation_in_progress"])
        self.assertTrue(detail["referral_message_generation_in_progress"])
        listed = self.client.get("/api/jobs/?section=main&date_from=2000-01-01&date_to=2100-01-01").json()
        self.assertTrue(listed[0]["referral_message_generation_in_progress"])

    def test_generation_response_and_detail_expose_page_count(self):
        document = self._cv_document(page_count=2)
        with patch("apps.jobs.views.request_manual_cv_generation", return_value=document):
            response = self.client.post(f"/api/jobs/{self.job.pk}/generate-cv/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["page_count"], 2)
        self.assertEqual(self._detail()["cv_page_count"], 2)


class UndoApplicationTests(_Base):
    def test_undo_returns_to_cv_generated_or_new_without_touching_inactivity_timer(self):
        for has_cv, expected in ((False, Job.Status.NEW), (True, Job.Status.CV_GENERATED)):
            if has_cv:
                self._cv_document()
            self.assertEqual(
                self.client.post(f"/api/jobs/{self.job.pk}/mark-application-done/").status_code, 200
            )
            self.user.refresh_from_db()
            reset_after_mark = self.user.last_activity_reset

            response = self.client.post(f"/api/jobs/{self.job.pk}/undo-application-done/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], expected)
            self.job.refresh_from_db()
            self.assertEqual(self.job.status, expected)
            self.assertIsNone(self.job.date_application_done)
            self.user.refresh_from_db()
            self.assertEqual(self.user.last_activity_reset, reset_after_mark)

    def test_undo_without_application_is_rejected(self):
        response = self.client.post(f"/api/jobs/{self.job.pk}/undo-application-done/")
        self.assertEqual(response.status_code, 409)


class GapNumberingTests(_Base):
    def test_prompt_uses_ui_numbering_and_text_in_list_order(self):
        lines = resolve_selected_gaps(self.job.score_gaps, gap_numbers=[3, 1, 99])
        self.assertEqual(lines, ["1. Kubernetes (motivo: richiesto)", "3. SAFe (motivo: certificazione)"])
        text = build_extra_instructions(lines, "per il gap 3 usa Acme")
        self.assertIn("1. Kubernetes", text)
        self.assertIn("3. SAFe", text)
        self.assertNotIn("2.", text)

    def test_legacy_gap_texts_get_their_list_number(self):
        lines = resolve_selected_gaps(self.job.score_gaps, gaps=["SAFe (certificazione)", "Altro"])
        self.assertEqual(lines, ["3. SAFe (motivo: certificazione)", "- Altro"])

    def test_generate_cv_endpoint_passes_numbered_gaps(self):
        with patch("apps.jobs.views.request_manual_cv_generation", return_value=self._cv_document()) as mock:
            self.client.post(
                f"/api/jobs/{self.job.pk}/generate-cv/",
                {"gap_numbers": [2], "gap_instructions": "per il gap 2 cita la certificazione"},
                format="json",
            )
        extra = mock.call_args.kwargs["extra_instructions"]
        self.assertIn("2. Inglese C1", extra)
        self.assertNotIn("1. Kubernetes", extra)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DraftReseedAndFinalizeTests(_Base):
    def test_outdated_draft_can_be_reseeded_or_kept(self):
        first = self._cv_document(_cv_content(summary="Primo"))
        self.assertEqual(self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/", {}, format="json").status_code, 201)
        self.assertEqual(CVDraft.objects.get(job=self.job).source_document, first)
        self.assertFalse(self._detail()["cv_draft_outdated"])

        draft = CVDraft.objects.get(job=self.job)
        draft.content_json["summary"] = "Modificato"
        draft.chat_history = [{"role": "user", "message": "ciao"}]
        draft.save()

        second = self._cv_document(_cv_content(summary="Secondo"))
        self.assertTrue(self._detail()["cv_draft_outdated"])

        kept = self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/", {"mode": "keep"}, format="json")
        self.assertEqual(kept.status_code, 200)
        self.assertEqual(kept.json()["summary"], "Modificato")
        self.assertFalse(self._detail()["cv_draft_outdated"])
        self.assertEqual(CVDraft.objects.get(job=self.job).source_document, second)

        self._cv_document(_cv_content(summary="Terzo"))
        reseeded = self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/", {}, format="json")
        self.assertEqual(reseeded.json()["summary"], "Terzo")
        draft.refresh_from_db()
        self.assertEqual(draft.chat_history, [])
        self.assertFalse(self._detail()["cv_draft_outdated"])

    def test_cover_letter_draft_reseed_conflict(self):
        self._cover_letter_document()
        self.client.post(f"/api/jobs/{self.job.pk}/cover-letter-draft/", {}, format="json")
        self.assertFalse(self._detail()["cover_letter_draft_outdated"])
        self._cover_letter_document(_cover_letter_content(("Nuovo.",)))
        self.assertTrue(self._detail()["cover_letter_draft_outdated"])
        reseeded = self.client.post(f"/api/jobs/{self.job.pk}/cover-letter-draft/", {}, format="json")
        self.assertEqual([p["text"] for p in reseeded.json()["paragraphs"]], ["Nuovo."])

    def test_finalize_saves_current_content_and_does_not_mark_draft_outdated(self):
        self._cv_document()
        self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/", {}, format="json")
        current = _cv_content(summary="Ultima modifica non salvata")
        with patch("apps.cv.draft.render_cv", return_value=("<html>x</html>", b"%PDF-1.4", 2)):
            response = self.client.post(
                f"/api/jobs/{self.job.pk}/cv-draft/finalize/", {"content": current}, format="json"
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["page_count"], 2)
        document = CVDocument.objects.get(pk=response.json()["cv_document_id"])
        self.assertEqual(document.content_json["summary"], "Ultima modifica non salvata")
        self.assertEqual(CVDraft.objects.get(job=self.job).content_json["summary"], "Ultima modifica non salvata")
        self.assertFalse(self._detail()["cv_draft_outdated"])

    def test_finalize_rejects_invalid_content(self):
        self._cv_document()
        self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/", {}, format="json")
        response = self.client.post(
            f"/api/jobs/{self.job.pk}/cv-draft/finalize/", {"content": {"summary": 1}}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_cover_letter_finalize_with_current_content(self):
        self._cover_letter_document()
        self.client.post(f"/api/jobs/{self.job.pk}/cover-letter-draft/", {}, format="json")
        with patch("apps.cv.cover_letter_draft.render_cover_letter", return_value=("<html/>", b"%PDF", 1)):
            response = self.client.post(
                f"/api/jobs/{self.job.pk}/cover-letter-draft/finalize/",
                {"content": _cover_letter_content(("Solo questo.",))},
                format="json",
            )
        self.assertEqual(response.status_code, 201)
        document = CoverLetterDocument.objects.get(pk=response.json()["cover_letter_document_id"])
        self.assertEqual(document.content_json["paragraphs"][0]["text"], "Solo questo.")

    def test_editable_flags_for_documents_without_content(self):
        self._cv_document(content={})
        self._cover_letter_document(content={})
        detail = self._detail()
        self.assertFalse(detail["cv_editable"])
        self.assertFalse(detail["cover_letter_editable"])
        self._cv_document()
        self.assertTrue(self._detail()["cv_editable"])


class StableIdsTests(_Base):
    def test_seed_from_legacy_document_assigns_bullet_ids(self):
        self._cv_document(_cv_content(with_ids=False))
        content = self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/", {}, format="json").json()
        ids = [b["id"] for b in content["experiences"][0]["bullets"]]
        self.assertEqual(len(set(ids)), 2)
        self.assertTrue(all(ids))

    def test_legacy_draft_is_normalized_and_legacy_actions_mapped(self):
        CVDraft.objects.create(
            job=self.job,
            user=self.user,
            content_json=_cv_content(with_ids=False),
            chat_history=[
                {"role": "user", "message": "x"},
                {
                    "role": "assistant",
                    "message": "ok",
                    "actions": [{"type": "update_bullet", "profile_experience_id": 7, "bullet_index": 1, "text": "Nuovo"}],
                },
            ],
        )
        content = self.client.get(f"/api/jobs/{self.job.pk}/cv-draft/").json()
        second_id = content["experiences"][0]["bullets"][1]["id"]
        history = self.client.get(f"/api/jobs/{self.job.pk}/cv-draft/chat/").json()["history"]
        self.assertEqual(history[1]["actions"][0]["bullet_id"], second_id)

    def test_patch_keeps_ids_and_fills_missing_ones(self):
        CVDraft.objects.create(job=self.job, user=self.user, content_json=_cv_content())
        payload = _cv_content()
        payload["experiences"][0]["bullets"].append({"text": "Aggiunto da una scheda vecchia", "shown": True})
        saved = self.client.patch(f"/api/jobs/{self.job.pk}/cv-draft/", payload, format="json").json()
        bullets = saved["experiences"][0]["bullets"]
        self.assertEqual([b["id"] for b in bullets[:2]], ["b0", "b1"])
        self.assertTrue(bullets[2]["id"])

    def test_cover_letter_string_paragraphs_are_normalized(self):
        CoverLetterDraft.objects.create(
            job=self.job,
            user=self.user,
            content_json={"content_language": "it", "translated_city": "Roma", "paragraphs": ["A", "B"]},
            chat_history=[{"role": "assistant", "message": "ok", "actions": [{"type": "remove_paragraph", "paragraph_index": 1, "text": None}]}],
        )
        content = self.client.get(f"/api/jobs/{self.job.pk}/cover-letter-draft/").json()
        self.assertEqual([p["text"] for p in content["paragraphs"]], ["A", "B"])
        history = self.client.get(f"/api/jobs/{self.job.pk}/cover-letter-draft/chat/").json()["history"]
        self.assertEqual(history[0]["actions"][0]["paragraph_id"], content["paragraphs"][1]["id"])


def _ai_reply(actions, reply="Ecco"):
    return {"reply": reply, "actions": actions}


def _cv_action(**fields):
    action = {
        "type": None, "profile_experience_id": None, "bullet_id": None, "area_index": None,
        "education_index": None, "language_index": None, "text": None, "name": None, "level": None,
    }
    action.update(fields)
    return action


class ChatActionsAndContextTests(_Base):
    def setUp(self):
        super().setUp()
        CVDraft.objects.create(job=self.job, user=self.user, content_json=_cv_content())
        CoverLetterDraft.objects.create(job=self.job, user=self.user, content_json=_cover_letter_content())

    def test_cv_chat_drops_actions_on_missing_ids_and_annotates_areas(self):
        actions = [
            _cv_action(type="update_bullet", bullet_id="b1", text="Migliorato"),
            _cv_action(type="hide_bullet", bullet_id="inesistente"),
            _cv_action(type="update_role", profile_experience_id=999, text="CTO"),
            _cv_action(type="remove_area", area_index=1),
            _cv_action(type="update_area", area_index=5, text="X"),
            _cv_action(type="update_education_notes", education_index=3, text="X"),
            _cv_action(type="update_summary", text=None),
        ]
        with patch("apps.cv.draft_chat.call_claude_structured", return_value=_ai_reply(actions)):
            response = self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/chat/", {"message": "migliora"}, format="json")
        self.assertEqual(response.status_code, 200)
        kept = response.json()["actions"]
        self.assertEqual([a["type"] for a in kept], ["update_bullet", "remove_area"])
        self.assertEqual(kept[0]["profile_experience_id"], 7)
        self.assertEqual(kept[1]["area_text"], "Budget")
        self.assertEqual(response.json()["balance"], "0.80")

    def test_cover_letter_chat_drops_actions_on_missing_paragraph_ids(self):
        actions = [
            {"type": "update_paragraph", "paragraph_id": "p1", "text": "Nuovo"},
            {"type": "remove_paragraph", "paragraph_id": "p9", "text": None},
            {"type": "add_paragraph", "paragraph_id": None, "text": "Aggiunto"},
        ]
        with patch("apps.cv.cover_letter_draft_chat.call_claude_structured", return_value=_ai_reply(actions)):
            response = self.client.post(
                f"/api/jobs/{self.job.pk}/cover-letter-draft/chat/", {"message": "x"}, format="json"
            )
        self.assertEqual([a["type"] for a in response.json()["actions"]], ["update_paragraph", "add_paragraph"])

    def test_two_removals_of_the_same_turn_target_their_own_paragraphs(self):
        actions = [
            {"type": "remove_paragraph", "paragraph_id": "p0", "text": None},
            {"type": "remove_paragraph", "paragraph_id": "p1", "text": None},
        ]
        with patch("apps.cv.cover_letter_draft_chat.call_claude_structured", return_value=_ai_reply(actions)):
            kept = self.client.post(
                f"/api/jobs/{self.job.pk}/cover-letter-draft/chat/", {"message": "x"}, format="json"
            ).json()["actions"]
        content = copy.deepcopy(_cover_letter_content())
        for action in kept:
            content["paragraphs"] = [p for p in content["paragraphs"] if p["id"] != action["paragraph_id"]]
        self.assertEqual([p["text"] for p in content["paragraphs"]], ["Chiusura."])

    def test_prompt_history_contains_previous_actions_with_decisions(self):
        draft = CVDraft.objects.get(job=self.job)
        draft.chat_history = [
            {"role": "user", "message": "rendi sintetico"},
            {
                "role": "assistant",
                "message": "ok",
                "actions": [
                    {**_cv_action(type="update_summary", text="Breve"), "decision": "accepted"},
                    {**_cv_action(type="hide_bullet", bullet_id="b0", profile_experience_id=7), "decision": "rejected"},
                    _cv_action(type="add_area", text="Nuova"),
                ],
            },
        ]
        draft.save()
        prompt = build_cv_chat_content(draft, self.job, self.profile, draft.chat_history, "e poi?", [])
        history = json.loads(prompt.split("CRONOLOGIA DELLA CONVERSAZIONE (dalla più vecchia):\n")[1].split("\n\nNUOVO")[0])
        decisions = [a["decision"] for a in history[1]["actions"]]
        self.assertEqual(decisions, ["accepted", "rejected", "pending"])
        self.assertEqual(history[1]["actions"][1]["bullet_id"], "b0")

        cl_draft = CoverLetterDraft.objects.get(job=self.job)
        cl_draft.chat_history = [
            {"role": "assistant", "message": "ok", "actions": [{"type": "remove_paragraph", "paragraph_id": "p0", "text": None, "decision": "rejected"}]}
        ]
        cl_prompt = build_cover_letter_chat_content(cl_draft, self.job, self.profile, cl_draft.chat_history, "x")
        self.assertIn('"decision": "rejected"', cl_prompt)
        self.assertIn('"paragraph_id": "p0"', cl_prompt)

    def test_focus_bullet_by_id(self):
        draft = CVDraft.objects.get(job=self.job)
        prompt = build_cv_chat_content(
            draft, self.job, self.profile, [], "questo", [{"profile_experience_id": 7, "bullet_id": "b1"}]
        )
        self.assertIn("Ridotto i costi.", prompt.split("BULLET PUNTATI DALL'UTENTE")[1])

    def test_chat_get_exposes_price_and_balance(self):
        for path in ("cv-draft/chat/", "cover-letter-draft/chat/"):
            data = self.client.get(f"/api/jobs/{self.job.pk}/{path}").json()
            self.assertEqual(data["price"], "0.20")
            self.assertEqual(data["balance"], "1.00")


class InstructionsHistoryTests(_Base):
    def test_combinations_and_case_variants_do_not_become_new_entries(self):
        for text in ["Tono diretto", "Tono diretto\n\nCita Acme", "  tono   DIRETTO ", "Cita Acme\n\nSii breve"]:
            self._cover_letter_document(instructions=text)
            ReferralMessageDocument.objects.create(
                job=self.job, user=self.user, channel="linkedin", content="x", instructions_used=text
            )
        expected = ["Cita Acme", "Sii breve", "tono   DIRETTO"]
        self.assertEqual(get_recent_cover_letter_instructions(self.user), expected)
        self.assertEqual(get_recent_referral_instructions(self.user), expected)


class BoldMarkupTests(TestCase):
    def test_bold_markers_rendered_in_summary_areas_role_and_notes(self):
        user = User.objects.create_user(username="bold@example.com", email="bold@example.com", password="pw-Bold-12345!")
        profile = Profile.objects.create(user=user)
        content = _cv_content(summary="Esperto di **Scrum** & <b>Agile</b>")
        content["areas_of_expertise"] = ["**Budget** control"]
        content["experiences"][0]["role"] = "**Senior** PM"
        content["educations"][0]["notes"] = "Tesi **110/110**"
        html, _pdf, _pages = render_cv(render_context_from_draft(user, profile, content))
        self.assertIn("Esperto di <strong>Scrum</strong> &amp; &lt;b&gt;Agile&lt;/b&gt;", html)
        self.assertIn("<strong>Budget</strong> control", html)
        self.assertIn("<strong>Senior</strong> PM", html)
        self.assertIn("Tesi <strong>110/110</strong>", html)
        self.assertNotIn("**", html)
