import tempfile
import threading
import time
import zoneinfo
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from rest_framework.test import APITestCase

from apps.cv.manual_generation import request_manual_cv_generation
from apps.cv.models import CVDocument
from apps.profiles.models import Education, Experience, Language, Profile
from apps.searches.models import SavedSearch

from .application import ApplicationMarkRejected, mark_application_done
from .collection import collect_jobs_for_user
from .import_service import (
    ImportDuplicate,
    ImportNotAllowed,
    ImportRejected,
    import_job_from_url,
)
from .list_service import list_jobs
from .manual_job_service import (
    MANUAL_JOB_DAILY_LIMIT,
    ManualJobRejected,
    create_manual_job,
)
from .models import DailyQuota, Job, RunLog
from .scoring import score_job, score_jobs
from .tasks import (
    CollectionAlreadyInProgress,
    CollectionDailyLimitReached,
    ManualCollectionFailed,
    run_manual_collection_for_user,
    run_nightly_cycle_for_user,
)

User = get_user_model()


def _offer(external_id, **overrides):
    offer = {
        "external_id": external_id,
        "title": "Project Manager",
        "company": "Acme S.p.A.",
        "location": "Roma",
        "description": "Descrizione della posizione.",
        "apply_url": "https://linkedin.com/jobs/view/123",
        "published_at": None,
        "salary": "",
    }
    offer.update(overrides)
    return offer


class CollectJobsForUserTests(TestCase):
    def setUp(self):
        self.free_user = User.objects.create_user(
            username="free@example.com", email="free@example.com", password="pw-Free-12345!"
        )
        SavedSearch.objects.create(
            user=self.free_user,
            keywords="Project Manager", city="Roma", country="Italia",
            is_active=True,
        )

    def test_no_cap_saves_every_valid_offer_regardless_of_plan(self):
        offers = [_offer(f"ext-{i}") for i in range(80)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            created = collect_jobs_for_user(self.free_user)

        self.assertEqual(len(created), 80)
        self.assertEqual(Job.objects.filter(user=self.free_user).count(), 80)

    def test_offer_missing_a_required_field_is_not_saved(self):
        offers = [_offer("ext-1"), _offer("ext-2", company="")]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            created = collect_jobs_for_user(self.free_user)

        self.assertEqual(len(created), 1)
        self.assertEqual(Job.objects.filter(user=self.free_user).count(), 1)

    def test_offer_with_apply_url_too_long_is_skipped_not_crashed(self):
        """Regressione (Sprint 49): un apply_url LinkedIn con tracking
        query-string oltre i 1000 caratteri del campo faceva fallire
        `Job.objects.create()` a metà batch, interrompendo l'intera
        raccolta e lasciando senza punteggio le offerte già create prima di
        quella malformata."""
        offers = [
            _offer("ext-1"),
            _offer("ext-2", apply_url="https://linkedin.com/jobs/view/123?" + "a" * 1000),
            _offer("ext-3"),
        ]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            created = collect_jobs_for_user(self.free_user)

        self.assertEqual({j.external_id for j in created}, {"ext-1", "ext-3"})

    def test_offer_without_published_at_is_saved_with_null(self):
        offers = [_offer("ext-1", published_at=None)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            collect_jobs_for_user(self.free_user)

        job = Job.objects.get(user=self.free_user, external_id="ext-1")
        self.assertIsNone(job.published_at)

    def test_rerunning_with_same_external_id_does_not_duplicate(self):
        offers = [_offer("ext-1")]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            collect_jobs_for_user(self.free_user)
            second_run_created = collect_jobs_for_user(self.free_user)

        self.assertEqual(len(second_run_created), 0)
        self.assertEqual(Job.objects.filter(user=self.free_user, external_id="ext-1").count(), 1)

    def test_no_cap_saves_every_valid_offer_for_pro_plan_too(self):
        pro_user = User.objects.create_user(
            username="pro@example.com",
            email="pro@example.com",
            password="pw-Pro-12345!",
            plan=User.Plan.PRO,
        )
        SavedSearch.objects.create(
            user=pro_user, keywords="PM", city="Roma", country="Italia", is_active=True
        )
        offers = [_offer(f"ext-{i}") for i in range(150)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            created = collect_jobs_for_user(pro_user)

        self.assertEqual(len(created), 150)

    def test_no_active_searches_collects_nothing(self):
        SavedSearch.objects.filter(user=self.free_user).update(is_active=False)
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            created = collect_jobs_for_user(self.free_user)
        mock_get_source.assert_not_called()
        self.assertEqual(created, [])

    def test_matched_search_from_offer_is_saved_on_the_job(self):
        offers = [_offer("ext-1", matched_search="Project Manager - Roma, Italia")]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            collect_jobs_for_user(self.free_user)

        job = Job.objects.get(user=self.free_user, external_id="ext-1")
        self.assertEqual(job.matched_search, "Project Manager - Roma, Italia")


FAKE_SCORE_RESULT = {
    "score": 4,
    "score_match": ["Esperienza di project management"],
    "score_gaps": ["Nessuna certificazione PMP"],
    "score_reasoning": "Buona affinità con il ruolo richiesto.",
    "language_check": {"required": False, "language": "", "international_exception": False},
}


class ScoreJobTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="score@example.com", email="score@example.com", password="pw-Score-12345!"
        )

    def _make_job(self, external_id):
        return Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id=external_id,
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione della posizione.",
            apply_url="https://linkedin.com/jobs/view/1",
        )

    def test_successful_scoring_populates_all_fields(self):
        job = self._make_job("ext-1")
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            result = score_job(job)

        self.assertTrue(result)
        job.refresh_from_db()
        self.assertEqual(job.score, 4)
        self.assertEqual(job.score_match, FAKE_SCORE_RESULT["score_match"])
        self.assertEqual(job.score_gaps, FAKE_SCORE_RESULT["score_gaps"])
        self.assertEqual(job.score_reasoning, FAKE_SCORE_RESULT["score_reasoning"])
        self.assertIsNotNone(job.date_scored)

    def test_failed_scoring_leaves_job_unscored_and_logs_run_log(self):
        job = self._make_job("ext-2")
        with patch(
            "apps.jobs.scoring.score_job_with_claude", side_effect=TimeoutError("timeout")
        ):
            result = score_job(job)

        self.assertFalse(result)
        job.refresh_from_db()
        self.assertIsNone(job.score)

        run_logs = RunLog.objects.filter(job=job, task_type=RunLog.TaskType.SCORING)
        self.assertEqual(run_logs.count(), 1)
        self.assertEqual(run_logs.first().status, RunLog.Status.FAILURE)

    def test_batch_scoring_isolates_single_job_failure(self):
        job_ok_1 = self._make_job("ext-3")
        job_fail = self._make_job("ext-4")
        job_ok_2 = self._make_job("ext-5")

        def fake_score(job, profile):
            if job.pk == job_fail.pk:
                raise RuntimeError("errore simulato")
            return FAKE_SCORE_RESULT

        with patch("apps.jobs.scoring.score_job_with_claude", side_effect=fake_score):
            scored = score_jobs([job_ok_1, job_fail, job_ok_2])

        self.assertEqual({job.pk for job in scored}, {job_ok_1.pk, job_ok_2.pk})
        job_fail.refresh_from_db()
        self.assertIsNone(job_fail.score)
        job_ok_1.refresh_from_db()
        self.assertEqual(job_ok_1.score, 4)

    def test_batch_scoring_runs_calls_concurrently(self):
        """Blocca una regressione a scoring sequenziale (Sprint 45): se
        `score_jobs` tornasse a chiamare `score_job_with_claude` un job alla
        volta, il picco di thread attivi in contemporanea sarebbe 1 e questo
        test fallirebbe."""
        jobs = [self._make_job(f"ext-concurrency-{i}") for i in range(8)]

        active = 0
        peak = 0
        lock = threading.Lock()

        def fake_score(job, profile):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.2)
            with lock:
                active -= 1
            return FAKE_SCORE_RESULT

        with patch("apps.jobs.scoring.score_job_with_claude", side_effect=fake_score):
            scored = score_jobs(jobs)

        self.assertEqual(len(scored), len(jobs))
        self.assertGreater(peak, 1)

    def test_language_mismatch_caps_score_regardless_of_model_value(self):
        """Il modello può assegnare un punteggio alto anche quando cita una
        lingua richiesta assente dal profilo (osservato in produzione,
        Sprint 48): il cap deterministico in scoring.py deve prevalere."""
        job = self._make_job("ext-lang-1")
        result = {
            **FAKE_SCORE_RESULT,
            "score": 9,
            "language_check": {"required": True, "language": "German", "international_exception": False},
        }
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=result):
            score_job(job)

        job.refresh_from_db()
        self.assertEqual(job.score, 3)
        self.assertIn("German", job.score_reasoning)

    def test_language_present_in_profile_is_not_capped(self):
        profile = Profile.objects.create(user=self.user)
        Language.objects.create(profile=profile, language="de", level="fluent")
        job = self._make_job("ext-lang-2")
        result = {
            **FAKE_SCORE_RESULT,
            "score": 9,
            "language_check": {"required": True, "language": "German", "international_exception": False},
        }
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=result):
            score_job(job)

        job.refresh_from_db()
        self.assertEqual(job.score, 9)

    def test_language_code_substring_does_not_cause_a_false_match(self):
        """Regressione: il codice lingua a due lettere ("es" per lo
        spagnolo) è una sottostringa di "Tedesco" — un confronto per
        sottostringa invece che per parola intera farebbe risultare il
        tedesco erroneamente già presente nel profilo."""
        profile = Profile.objects.create(user=self.user)
        Language.objects.create(profile=profile, language="es", level="fluent")
        job = self._make_job("ext-lang-4")
        result = {
            **FAKE_SCORE_RESULT,
            "score": 9,
            "language_check": {"required": True, "language": "Tedesco", "international_exception": False},
        }
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=result):
            score_job(job)

        job.refresh_from_db()
        self.assertEqual(job.score, 3)

    def test_international_exception_skips_the_cap(self):
        job = self._make_job("ext-lang-3")
        result = {
            **FAKE_SCORE_RESULT,
            "score": 9,
            "language_check": {"required": True, "language": "German", "international_exception": True},
        }
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=result):
            score_job(job)

        job.refresh_from_db()
        self.assertEqual(job.score, 9)


class RunNightlyCycleForUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="nightly@example.com", email="nightly@example.com", password="pw-Night-12345!"
        )
        SavedSearch.objects.create(
            user=self.user, keywords="PM", city="Roma", country="Italia", is_active=True
        )

    def test_orchestrates_collection_and_scoring_with_run_log_no_cap(self):
        offers = [_offer(f"ext-{i}") for i in range(20)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            summary = run_nightly_cycle_for_user(self.user)

        self.assertEqual(summary["collected"], 20)
        self.assertEqual(summary["scored"], 20)
        self.assertEqual(summary["kept"], 20)
        self.assertNotIn("discarded_cap", summary)
        self.assertEqual(Job.objects.filter(user=self.user, discarded_by_cap=True).count(), 0)

        run_log = RunLog.objects.get(user=self.user, task_type=RunLog.TaskType.COLLECTION)
        self.assertEqual(run_log.status, RunLog.Status.SUCCESS)
        self.assertIn("raccolti=20", run_log.message)
        self.assertNotIn("scartati_cap", run_log.message)


class NoAutomaticCvGenerationInNightlyCycleTests(TestCase):
    """La generazione automatica di CV è stata rimossa: il ciclo
    di raccolta lascia sempre i job in `new`, indipendentemente dallo score —
    la generazione resta sempre manuale (§4.7/§4.11 funzionali)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="noautocv@example.com", email="noautocv@example.com", password="pw-NoAuto-12345!"
        )
        SavedSearch.objects.create(
            user=self.user, keywords="PM", city="Roma", country="Italia", is_active=True
        )

    def test_high_score_jobs_stay_new_and_no_cv_is_generated(self):
        offers = [_offer(f"ext-{i}") for i in range(5)]
        scores = iter([5, 4, 3, 2, 1])

        def fake_score(job, profile):
            return {**FAKE_SCORE_RESULT, "score": next(scores)}

        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", side_effect=fake_score
        ), patch("apps.cv.generation.generate_cv") as mock_generate_cv:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            summary = run_nightly_cycle_for_user(self.user)

        self.assertNotIn("cv_generated", summary)
        mock_generate_cv.assert_not_called()
        self.assertTrue(all(job.status == Job.Status.NEW for job in Job.objects.filter(user=self.user)))
        self.assertFalse(CVDocument.objects.filter(job__user=self.user).exists())


class RunManualCollectionForUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="manualcollect@example.com",
            email="manualcollect@example.com",
            password="pw-Manual-12345!",
        )
        SavedSearch.objects.create(
            user=self.user, keywords="PM", city="Roma", country="Italia", is_active=True
        )

    def test_runs_collection_and_scoring_and_releases_guard(self):
        offers = [_offer(f"ext-{i}") for i in range(3)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            summary = run_manual_collection_for_user(self.user)

        self.assertEqual(summary["collected"], 3)
        self.user.refresh_from_db()
        self.assertFalse(self.user.collection_in_progress)
        self.assertIsNone(self.user.collection_started_at)

    def test_rejects_when_already_in_progress(self):
        self.user.collection_in_progress = True
        self.user.collection_started_at = timezone.now()
        self.user.save(update_fields=["collection_in_progress", "collection_started_at"])

        with self.assertRaises(CollectionAlreadyInProgress):
            run_manual_collection_for_user(self.user)

    def test_allows_new_collection_when_previous_flag_is_stale(self):
        """Bug osservato in produzione (sprint corrente): un riavvio del
        server durante una raccolta lascia `collection_in_progress=True` per
        sempre, perché il `finally` che lo rimette a `False` non viene mai
        eseguito. Dopo `COLLECTION_STALE_AFTER` il flag va ignorato invece
        di bloccare l'utente a tempo indeterminato."""
        self.user.collection_in_progress = True
        self.user.collection_started_at = timezone.now() - timedelta(hours=3)
        self.user.save(update_fields=["collection_in_progress", "collection_started_at"])

        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=[]))
            summary = run_manual_collection_for_user(self.user)

        self.assertEqual(summary["collected"], 0)
        self.user.refresh_from_db()
        self.assertFalse(self.user.collection_in_progress)

    def test_allows_new_collection_when_flag_has_no_timestamp(self):
        """`collection_in_progress=True` senza `collection_started_at` (flag
        rimasto `True` da prima che questo campo esistesse, osservato in
        produzione appena dopo aver introdotto il timeout): l'età non è
        verificabile, va trattato come stantio, non come blocco permanente."""
        self.user.collection_in_progress = True
        self.user.collection_started_at = None
        self.user.save(update_fields=["collection_in_progress", "collection_started_at"])

        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=[]))
            summary = run_manual_collection_for_user(self.user)

        self.assertEqual(summary["collected"], 0)

    def test_rejects_when_flag_is_recent_even_if_set_a_bit_ago(self):
        self.user.collection_in_progress = True
        self.user.collection_started_at = timezone.now() - timedelta(minutes=5)
        self.user.save(update_fields=["collection_in_progress", "collection_started_at"])

        with self.assertRaises(CollectionAlreadyInProgress):
            run_manual_collection_for_user(self.user)

    def test_releases_guard_and_logs_failure_on_source_error(self):
        with patch(
            "apps.jobs.collection.get_job_source",
            side_effect=ConnectionError("fonte non raggiungibile"),
        ):
            with self.assertRaises(ManualCollectionFailed):
                run_manual_collection_for_user(self.user)

        self.user.refresh_from_db()
        self.assertFalse(self.user.collection_in_progress)
        run_log = RunLog.objects.get(user=self.user, task_type=RunLog.TaskType.COLLECTION)
        self.assertEqual(run_log.status, RunLog.Status.FAILURE)

    def _collect_once(self):
        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=[]))
            return run_manual_collection_for_user(self.user)

    def test_second_call_same_day_hits_the_daily_limit(self):
        self._collect_once()

        with self.assertRaises(CollectionDailyLimitReached):
            self._collect_once()

        quota = DailyQuota.objects.get(user=self.user)
        self.assertEqual(quota.collection_count, 1)

    def test_failed_collection_refunds_the_daily_quota(self):
        with patch(
            "apps.jobs.collection.get_job_source",
            side_effect=ConnectionError("fonte non raggiungibile"),
        ):
            with self.assertRaises(ManualCollectionFailed):
                run_manual_collection_for_user(self.user)

        quota = DailyQuota.objects.get(user=self.user)
        self.assertEqual(quota.collection_count, 0)
        # Il fallimento restituisce la quota: una nuova richiesta lo stesso
        # giorno deve poter procedere di nuovo.
        summary = self._collect_once()
        self.assertEqual(summary["collected"], 0)


class CollectJobsApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="collectapi@example.com",
            email="collectapi@example.com",
            password="pw-CollectApi-12345!",
        )
        self.client.force_authenticate(user=self.user)
        SavedSearch.objects.create(
            user=self.user, keywords="PM", city="Roma", country="Italia", is_active=True
        )

    def test_post_collects_for_the_authenticated_user_only(self):
        other_user = User.objects.create_user(
            username="other-collectapi@example.com",
            email="other-collectapi@example.com",
            password="pw-Other-12345!",
        )
        offers = [_offer("ext-collect-0")]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            response = self.client.post("/api/jobs/collect/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["collected"], 1)
        self.assertTrue(Job.objects.filter(user=self.user, external_id="ext-collect-0").exists())
        self.assertFalse(Job.objects.filter(user=other_user).exists())

    def test_post_returns_409_when_already_in_progress(self):
        self.user.collection_in_progress = True
        self.user.collection_started_at = timezone.now()
        self.user.save(update_fields=["collection_in_progress", "collection_started_at"])

        response = self.client.post("/api/jobs/collect/")

        self.assertEqual(response.status_code, 409)

    def test_post_returns_409_on_second_call_same_day(self):
        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=[]))
            first = self.client.post("/api/jobs/collect/")
            second = self.client.post("/api/jobs/collect/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)


class NightlyCycleScheduleTests(TestCase):
    def test_periodic_task_is_scheduled_at_2am_europe_rome(self):
        task = PeriodicTask.objects.get(
            name="Ciclo notturno (raccolta, scoring, cap di intake)"
        )
        self.assertEqual(task.task, "apps.jobs.tasks.run_nightly_cycle")
        self.assertTrue(task.enabled)
        self.assertEqual(task.crontab.hour, "2")
        self.assertEqual(task.crontab.minute, "0")
        self.assertEqual(str(task.crontab.timezone), "Europe/Rome")


class RunNightlyCycleOrchestratorTests(TestCase):
    """Sprint 22, §6 "comportamento in caso di fonte non disponibile": un
    fallimento per un singolo utente (es. sorgente Apify irraggiungibile) non
    deve bloccare la raccolta per gli utenti successivi del batch — bug reale
    trovato durante la QA di fine sprint (`run_nightly_cycle` non isolava le
    eccezioni per utente)."""

    def setUp(self):
        self.failing_user = User.objects.create_user(
            username="nightly-fail@example.com",
            email="nightly-fail@example.com",
            password="pw-Fail-12345!",
        )
        self.healthy_user = User.objects.create_user(
            username="nightly-ok@example.com", email="nightly-ok@example.com", password="pw-Ok-12345!"
        )

    def test_failure_for_one_user_does_not_block_the_rest_of_the_batch(self):
        from . import tasks as tasks_module

        processed = []

        def fake_run_for_user(user):
            processed.append(user.pk)
            if user.pk == self.failing_user.pk:
                raise ConnectionError("fonte non raggiungibile")
            return {}

        with patch.object(tasks_module, "run_nightly_cycle_for_user", side_effect=fake_run_for_user):
            tasks_module.run_nightly_cycle()

        self.assertEqual(set(processed), {self.failing_user.pk, self.healthy_user.pk})

        run_log = RunLog.objects.get(user=self.failing_user, task_type=RunLog.TaskType.COLLECTION)
        self.assertEqual(run_log.status, RunLog.Status.FAILURE)
        self.assertIn("fonte non raggiungibile", run_log.message)


VALID_LINKEDIN_URL = "https://www.linkedin.com/jobs/view/1234567890"


def _import_offer(**overrides):
    offer = {
        "external_id": "1234567890",
        "title": "Site Supervisor",
        "company": "Kuwait Petroleum",
        "location": "Kuwait City",
        "description": "Descrizione della posizione importata.",
        "apply_url": VALID_LINKEDIN_URL,
        "published_at": None,
        "salary": "",
    }
    offer.update(overrides)
    return offer


@override_settings(PRICE_IMPORT_EXTRA=Decimal("0.50"))
class ImportJobTests(TestCase):
    def _make_user(self, plan=User.Plan.FREE, extra_credit=Decimal("0")):
        return User.objects.create_user(
            username=f"import-{plan}-{extra_credit}@example.com",
            email=f"import-{plan}-{extra_credit}@example.com",
            password="pw-Import-12345!",
            plan=plan,
            extra_credit=extra_credit,
        )

    def test_pro_user_imports_valid_link_scored_without_automatic_cv(self):
        user = self._make_user(plan=User.Plan.PRO)

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(return_value=_import_offer())
            )
            job = import_job_from_url(user, VALID_LINKEDIN_URL)

        self.assertEqual(job.origin, Job.Origin.IMPORTED)
        self.assertEqual(job.status, Job.Status.NEW)
        self.assertEqual(job.score, FAKE_SCORE_RESULT["score"])
        self.assertFalse(CVDocument.objects.filter(job=job).exists())

    def test_free_user_cannot_import_even_with_credit(self):
        user = self._make_user(plan=User.Plan.FREE, extra_credit=Decimal("100"))

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source:
            with self.assertRaises(ImportNotAllowed):
                import_job_from_url(user, VALID_LINKEDIN_URL)
            mock_get_source.assert_not_called()

        self.assertEqual(Job.objects.filter(user=user).count(), 0)
        self.assertFalse(DailyQuota.objects.filter(user=user).exists())

    def test_invalid_link_is_rejected_without_creating_a_job(self):
        user = self._make_user(plan=User.Plan.PRO)

        with self.assertRaises(ImportRejected):
            import_job_from_url(user, "https://example.com/not-a-linkedin-job")

        self.assertEqual(Job.objects.filter(user=user).count(), 0)

    def test_importing_an_already_present_job_is_flagged_as_duplicate(self):
        user = self._make_user(plan=User.Plan.PRO)
        Job.objects.create(
            user=user,
            source=Job.Source.LINKEDIN,
            external_id="1234567890",
            title="Site Supervisor",
            company="Kuwait Petroleum",
            location="Kuwait City",
            description="Già presente.",
            apply_url=VALID_LINKEDIN_URL,
        )

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source:
            with self.assertRaises(ImportDuplicate):
                import_job_from_url(user, VALID_LINKEDIN_URL)
            mock_get_source.assert_not_called()

        self.assertEqual(Job.objects.filter(user=user).count(), 1)
        self.assertFalse(DailyQuota.objects.filter(user=user).exists())

    def _import_n(self, user, count, start=1000):
        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            for i in range(count):
                mock_get_source.return_value = MagicMock(
                    fetch_by_url=MagicMock(
                        return_value=_import_offer(
                            external_id=f"ext-{start + i}",
                            apply_url=f"{VALID_LINKEDIN_URL}-{start + i}",
                        )
                    )
                )
                import_job_from_url(user, f"https://www.linkedin.com/jobs/view/{start + i}")

    def test_fourth_import_without_credit_is_rejected(self):
        user = self._make_user(plan=User.Plan.PRO, extra_credit=Decimal("0"))
        self._import_n(user, 3)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.import_count, 3)

        with self.assertRaises(ImportRejected):
            import_job_from_url(user, "https://www.linkedin.com/jobs/view/2000")

        quota.refresh_from_db()
        self.assertEqual(quota.import_count, 3)

    def test_fourth_import_with_enough_credit_proceeds_and_scales_price(self):
        user = self._make_user(plan=User.Plan.PRO, extra_credit=Decimal("5.00"))
        self._import_n(user, 3)

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(
                    return_value=_import_offer(external_id="ext-2000", apply_url=f"{VALID_LINKEDIN_URL}-2000")
                )
            )
            import_job_from_url(user, "https://www.linkedin.com/jobs/view/2000")

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.import_count, 3)
        user.refresh_from_db()
        self.assertEqual(user.extra_credit, Decimal("4.50"))

    def test_import_and_manual_cv_generation_consume_separate_counters(self):
        user = self._make_user(plan=User.Plan.PRO)
        profile = Profile.objects.create(user=user)
        Education.objects.create(
            profile=profile, institution="Università di Roma", title="Laurea", end_date="2015-07-01"
        )

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(return_value=_import_offer())
            )
            job = import_job_from_url(user, VALID_LINKEDIN_URL)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.import_count, 1)
        self.assertEqual(quota.manual_cv_count, 0)

        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(job)

        quota.refresh_from_db()
        self.assertEqual(quota.import_count, 1)
        self.assertEqual(quota.manual_cv_count, 1)


class ImportJobApiTests(APITestCase):
    """Endpoint HTTP dell'import manuale (`POST /api/jobs/import/`), non
    ancora esposto in UI finché non è stato collegato un pulsante — la logica
    di servizio è già coperta a fondo da `ImportJobTests`, qui si verifica
    solo l'esposizione via API (status code e messaggi d'errore)."""

    def _make_user(self, plan=User.Plan.PRO):
        return User.objects.create_user(
            username=f"import-api-{plan}@example.com",
            email=f"import-api-{plan}@example.com",
            password="pw-ImportApi-12345!",
            plan=plan,
        )

    def test_pro_user_imports_via_api(self):
        user = self._make_user(plan=User.Plan.PRO)
        self.client.force_authenticate(user)

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(return_value=_import_offer())
            )
            response = self.client.post(
                "/api/jobs/import/", {"url": VALID_LINKEDIN_URL}, format="json"
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Job.objects.filter(pk=response.data["job_id"]).exists())

    def test_free_user_is_rejected_via_api(self):
        user = self._make_user(plan=User.Plan.FREE)
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/jobs/import/", {"url": VALID_LINKEDIN_URL}, format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_link_is_rejected_via_api(self):
        user = self._make_user(plan=User.Plan.PRO)
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/jobs/import/", {"url": "https://example.com/not-a-job"}, format="json"
        )

        self.assertEqual(response.status_code, 409)


def _manual_job_data(**overrides):
    data = {
        "title": "Business Analyst",
        "company": "Acme S.p.A.",
        "location": "Roma",
        "description": "Descrizione della posizione inserita a mano.",
        "published_at": timezone.now(),
    }
    data.update(overrides)
    return data


@override_settings(PRICE_MANUAL_JOB_EXTRA=Decimal("0.50"))
class ManualJobCreationTests(TestCase):
    def _make_user(self, plan=User.Plan.FREE, extra_credit=Decimal("0")):
        return User.objects.create_user(
            username=f"manual-job-{plan}-{extra_credit}@example.com",
            email=f"manual-job-{plan}-{extra_credit}@example.com",
            password="pw-ManualJob-12345!",
            plan=plan,
            extra_credit=extra_credit,
        )

    def test_free_user_can_create_a_manual_job_scored_without_automatic_cv(self):
        # A differenza dell'import da LinkedIn, la creazione manuale non è
        # riservata al piano Pro.
        user = self._make_user(plan=User.Plan.FREE)

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            job = create_manual_job(user, _manual_job_data())

        self.assertEqual(job.source, Job.Source.MANUAL)
        self.assertEqual(job.origin, Job.Origin.IMPORTED)
        self.assertEqual(job.status, Job.Status.NEW)
        self.assertEqual(job.score, FAKE_SCORE_RESULT["score"])
        self.assertEqual(job.apply_url, "")
        self.assertFalse(CVDocument.objects.filter(job=job).exists())

    def test_apply_url_is_optional_but_saved_when_provided(self):
        user = self._make_user(plan=User.Plan.PRO)

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            job = create_manual_job(
                user, _manual_job_data(apply_url="https://example.com/apply")
            )

        self.assertEqual(job.apply_url, "https://example.com/apply")

    def test_external_id_is_unique_per_job_avoiding_constraint_collisions(self):
        user = self._make_user(plan=User.Plan.PRO)

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            first = create_manual_job(user, _manual_job_data())
            second = create_manual_job(user, _manual_job_data())

        self.assertNotEqual(first.external_id, second.external_id)

    def _create_n(self, user, count):
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            for _ in range(count):
                create_manual_job(user, _manual_job_data())

    def test_fourth_manual_job_without_credit_is_rejected(self):
        user = self._make_user(plan=User.Plan.FREE, extra_credit=Decimal("0"))
        self._create_n(user, MANUAL_JOB_DAILY_LIMIT)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_job_count, MANUAL_JOB_DAILY_LIMIT)

        with self.assertRaises(ManualJobRejected):
            create_manual_job(user, _manual_job_data())

        quota.refresh_from_db()
        self.assertEqual(quota.manual_job_count, MANUAL_JOB_DAILY_LIMIT)

    def test_fourth_manual_job_with_enough_credit_proceeds_and_scales_price(self):
        user = self._make_user(plan=User.Plan.FREE, extra_credit=Decimal("5.00"))
        self._create_n(user, MANUAL_JOB_DAILY_LIMIT)

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            create_manual_job(user, _manual_job_data())

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_job_count, MANUAL_JOB_DAILY_LIMIT)
        user.refresh_from_db()
        self.assertEqual(user.extra_credit, Decimal("4.50"))

    def test_manual_job_creation_and_linkedin_import_consume_separate_counters(self):
        user = self._make_user(plan=User.Plan.PRO)

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            create_manual_job(user, _manual_job_data())

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(return_value=_import_offer())
            )
            import_job_from_url(user, VALID_LINKEDIN_URL)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_job_count, 1)
        self.assertEqual(quota.import_count, 1)


class CreateManualJobApiTests(APITestCase):
    def _make_user(self, plan=User.Plan.FREE):
        return User.objects.create_user(
            username=f"manual-job-api-{plan}@example.com",
            email=f"manual-job-api-{plan}@example.com",
            password="pw-ManualJobApi-12345!",
            plan=plan,
        )

    def test_free_user_creates_a_manual_job_via_api(self):
        user = self._make_user(plan=User.Plan.FREE)
        self.client.force_authenticate(user)

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            response = self.client.post(
                "/api/jobs/manual/",
                {
                    "title": "Business Analyst",
                    "company": "Acme S.p.A.",
                    "location": "Roma",
                    "description": "Descrizione della posizione.",
                    "published_at": timezone.now().isoformat(),
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Job.objects.filter(pk=response.data["job_id"]).exists())

    def test_missing_required_field_is_rejected_with_400(self):
        user = self._make_user(plan=User.Plan.FREE)
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/jobs/manual/",
            {
                "title": "Business Analyst",
                "company": "Acme S.p.A.",
                # "location" mancante.
                "description": "Descrizione della posizione.",
                "published_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("location", response.data)


class JobListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="list@example.com",
            email="list@example.com",
            password="pw-List-12345!",
            timezone="Europe/Rome",
        )

    def _make_job(
        self,
        external_id,
        origin=Job.Origin.COLLECTED,
        is_archived=False,
        status=Job.Status.NEW,
        score=None,
        days_ago=0,
        title="Project Manager",
        company="Acme S.p.A.",
        location="Roma",
        matched_search="",
    ):
        job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id=external_id,
            title=title,
            company=company,
            location=location,
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            origin=origin,
            is_archived=is_archived,
            status=status,
            score=score,
            matched_search=matched_search,
        )
        if days_ago:
            Job.objects.filter(pk=job.pk).update(
                date_collected=timezone.now() - timedelta(days=days_ago)
            )
            job.refresh_from_db()
        return job

    def _local_today(self, user=None):
        user = user or self.user
        tz = zoneinfo.ZoneInfo(user.timezone)
        return timezone.now().astimezone(tz).date()

    def test_sections_return_exactly_the_expected_jobs(self):
        main_job = self._make_job("main-1", origin=Job.Origin.COLLECTED, is_archived=False)
        imported_job = self._make_job("imported-1", origin=Job.Origin.IMPORTED, is_archived=False)
        archived_collected = self._make_job(
            "archived-collected-1", origin=Job.Origin.COLLECTED, is_archived=True
        )
        archived_imported = self._make_job(
            "archived-imported-1", origin=Job.Origin.IMPORTED, is_archived=True
        )

        main_ids = {job.pk for job in list_jobs(self.user, "main")}
        imported_ids = {job.pk for job in list_jobs(self.user, "imported")}
        archived_ids = {job.pk for job in list_jobs(self.user, "archived")}

        self.assertEqual(main_ids, {main_job.pk})
        self.assertEqual(imported_ids, {imported_job.pk})
        self.assertEqual(archived_ids, {archived_collected.pk, archived_imported.pk})

    def test_favorites_section_excludes_archived_favorites(self):
        favorite_main = self._make_job("fav-main", origin=Job.Origin.COLLECTED, is_archived=False)
        favorite_main.is_favorite = True
        favorite_main.save(update_fields=["is_favorite"])

        favorite_archived = self._make_job(
            "fav-archived", origin=Job.Origin.COLLECTED, is_archived=True
        )
        favorite_archived.is_favorite = True
        favorite_archived.save(update_fields=["is_favorite"])

        self._make_job("not-fav", origin=Job.Origin.COLLECTED, is_archived=False)

        favorites_ids = {job.pk for job in list_jobs(self.user, "favorites")}
        archived_ids = {job.pk for job in list_jobs(self.user, "archived")}

        self.assertEqual(favorites_ids, {favorite_main.pk})
        self.assertIn(favorite_archived.pk, archived_ids)
        self.assertNotIn(favorite_archived.pk, favorites_ids)

    def test_date_range_filter_returns_only_jobs_collected_in_range(self):
        today_job = self._make_job("today-1", days_ago=0)
        old_job = self._make_job("old-1", days_ago=2)
        today = self._local_today()

        results = list_jobs(self.user, "main", date_from=today, date_to=today)

        result_ids = {job.pk for job in results}
        self.assertIn(today_job.pk, result_ids)
        self.assertNotIn(old_job.pk, result_ids)

    def test_no_date_range_returns_entire_history(self):
        today_job = self._make_job("today-2", days_ago=0)
        old_job = self._make_job("old-2", days_ago=60)

        results = list_jobs(self.user, "main")

        result_ids = {job.pk for job in results}
        self.assertEqual(result_ids, {today_job.pk, old_job.pk})

    def test_date_range_filter_uses_each_users_own_timezone(self):
        """Sprint 22, §7 requisiti trasversali: la conversione di una data
        nell'istante UTC segue il fuso locale dell'utente, non un
        riferimento unico di sistema. Stesso istante assoluto di raccolta,
        due utenti su fusi diversi: chi è già "domani" nel proprio fuso non
        lo trova più filtrando per il giorno di ieri, chi è ancora "ieri" sì.
        """
        kiribati_user = User.objects.create_user(
            username="list-kiribati@example.com",
            email="list-kiribati@example.com",
            password="pw-Kiribati-12345!",
            timezone="Pacific/Kiritimati",
        )

        # 21:30 UTC del 27/07: le 23:30 CEST del 27/07 a Roma (ancora "27"
        # lì), ma le 11:30 (+14) del 28/07 a Kiritimati (già "28" lì).
        job_instant = timezone.datetime(2026, 7, 27, 21, 30, tzinfo=timezone.get_fixed_timezone(0))
        target_day = date(2026, 7, 27)

        rome_job = self._make_job("tz-rome-1")
        Job.objects.filter(pk=rome_job.pk).update(date_collected=job_instant)

        kiribati_job = Job.objects.create(
            user=kiribati_user,
            source=Job.Source.LINKEDIN,
            external_id="tz-kiribati-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
        )
        Job.objects.filter(pk=kiribati_job.pk).update(date_collected=job_instant)

        rome_ids = {
            job.pk for job in list_jobs(self.user, "main", date_from=target_day, date_to=target_day)
        }
        kiribati_ids = {
            job.pk
            for job in list_jobs(kiribati_user, "main", date_from=target_day, date_to=target_day)
        }

        self.assertIn(rome_job.pk, rome_ids)
        self.assertNotIn(kiribati_job.pk, kiribati_ids)

    def test_score_and_status_filters_intersect_correctly_in_every_section(self):
        sections = [
            ("main", {"origin": Job.Origin.COLLECTED, "is_archived": False}),
            ("imported", {"origin": Job.Origin.IMPORTED, "is_archived": False}),
            ("archived", {"origin": Job.Origin.COLLECTED, "is_archived": True}),
        ]
        for section, section_kwargs in sections:
            match = self._make_job(
                f"{section}-match", score=5, status=Job.Status.NEW, **section_kwargs
            )
            self._make_job(
                f"{section}-wrong-score", score=3, status=Job.Status.NEW, **section_kwargs
            )
            self._make_job(
                f"{section}-wrong-status",
                score=5,
                status=Job.Status.CV_GENERATED,
                **section_kwargs,
            )

            results = list_jobs(self.user, section, scores=[4, 5], statuses=[Job.Status.NEW])
            self.assertEqual({job.pk for job in results}, {match.pk})

    def test_results_are_always_ordered_by_score_descending(self):
        low = self._make_job("order-low", score=2)
        high = self._make_job("order-high", score=5)
        mid = self._make_job("order-mid", score=3)

        results = list(list_jobs(self.user, "main"))

        self.assertEqual([job.pk for job in results], [high.pk, mid.pk, low.pk])

    def test_search_is_confined_to_current_section_and_ignores_other_filters(self):
        main_match = self._make_job(
            "search-main", origin=Job.Origin.COLLECTED, is_archived=False, title="Rare Keyword Match"
        )
        self._make_job(
            "search-archived",
            origin=Job.Origin.COLLECTED,
            is_archived=True,
            title="Rare Keyword Match",
        )
        self._make_job(
            "search-imported",
            origin=Job.Origin.IMPORTED,
            is_archived=False,
            title="Rare Keyword Match",
        )

        # Filtri palesemente contraddittori (data/score/stato/location
        # impossibili da soddisfare insieme al titolo): devono essere
        # ignorati quando la ricerca testuale è attiva.
        results = list_jobs(
            self.user,
            "main",
            date_from=date(2000, 1, 1),
            date_to=date(2000, 1, 2),
            scores=[1],
            statuses=[Job.Status.APPLICATION_DONE],
            query="Rare Keyword",
            location="Nessun posto del genere",
        )

        self.assertEqual({job.pk for job in results}, {main_match.pk})

    def test_search_filter_matches_job_role_saved_search_by_reconstructed_string(self):
        job_role_search = SavedSearch.objects.create(
            user=self.user,
            search_type=SavedSearch.SearchType.JOB_ROLE,
            keywords="Business analyst",
            city="Zurich",
            country="Switzerland",
        )
        match = self._make_job(
            "search-jobrole-match", matched_search="Business analyst - Zurich, Switzerland"
        )
        self._make_job("search-jobrole-other", matched_search="IT Project manager - Zurich, Switzerland")

        results = list_jobs(self.user, "main", search_ids=[str(job_role_search.pk)])

        self.assertEqual({job.pk for job in results}, {match.pk})

    def test_search_filter_matches_company_saved_search_case_insensitively(self):
        company_search = SavedSearch.objects.create(
            user=self.user,
            search_type=SavedSearch.SearchType.COMPANY,
            keywords="UBS",
            city="Zurich",
            country="Switzerland",
        )
        # Il nome restituito da LinkedIn può avere una capitalizzazione
        # diversa da quella digitata dall'utente nella ricerca salvata.
        match = self._make_job("search-company-match", matched_search="ubs")
        self._make_job("search-company-other", matched_search="Deloitte")

        results = list_jobs(self.user, "main", search_ids=[str(company_search.pk)])

        self.assertEqual({job.pk for job in results}, {match.pk})

    def test_search_filter_none_isolates_jobs_without_matched_search(self):
        imported_like = self._make_job("search-none-match", matched_search="")
        self._make_job("search-none-other", matched_search="UBS")

        results = list_jobs(self.user, "main", search_ids=["none"])

        self.assertEqual({job.pk for job in results}, {imported_like.pk})

    def test_no_search_filter_returns_everything(self):
        job_a = self._make_job("search-all-a", matched_search="UBS")
        job_b = self._make_job("search-all-b", matched_search="")

        results = list_jobs(self.user, "main", search_ids=None)

        self.assertEqual({job.pk for job in results}, {job_a.pk, job_b.pk})

    def test_search_filter_with_unknown_id_returns_no_results(self):
        self._make_job("search-unknown", matched_search="UBS")

        results = list_jobs(self.user, "main", search_ids=["999999"])

        self.assertEqual(list(results), [])

    def test_search_filter_combines_multiple_ids_with_or(self):
        job_role_search = SavedSearch.objects.create(
            user=self.user,
            search_type=SavedSearch.SearchType.JOB_ROLE,
            keywords="Business analyst",
            city="Zurich",
            country="Switzerland",
        )
        company_search = SavedSearch.objects.create(
            user=self.user,
            search_type=SavedSearch.SearchType.COMPANY,
            keywords="UBS",
            city="Zurich",
            country="Switzerland",
        )
        match_job_role = self._make_job(
            "multi-match-jobrole", matched_search="Business analyst - Zurich, Switzerland"
        )
        match_company = self._make_job("multi-match-company", matched_search="ubs")
        no_match = self._make_job("multi-no-match", matched_search="Deloitte")

        results = list_jobs(
            self.user, "main", search_ids=[str(job_role_search.pk), str(company_search.pk)]
        )

        self.assertEqual({job.pk for job in results}, {match_job_role.pk, match_company.pk})
        self.assertNotIn(no_match.pk, {job.pk for job in results})

    def test_search_filter_ignores_unknown_id_when_combined_with_a_valid_one(self):
        """A differenza della vecchia versione a singola selezione, un id
        sconosciuto nella lista non deve annullare il contributo degli id
        validi selezionati insieme ad esso."""
        valid_search = SavedSearch.objects.create(
            user=self.user,
            search_type=SavedSearch.SearchType.COMPANY,
            keywords="UBS",
            city="Zurich",
            country="Switzerland",
        )
        match = self._make_job("multi-unknown-match", matched_search="ubs")
        self._make_job("multi-unknown-other", matched_search="Deloitte")

        results = list_jobs(self.user, "main", search_ids=[str(valid_search.pk), "999999"])

        self.assertEqual({job.pk for job in results}, {match.pk})

    def test_search_filter_does_not_match_another_users_saved_search(self):
        other_user = User.objects.create_user(
            username="other-search@example.com",
            email="other-search@example.com",
            password="pw-Other-12345!",
        )
        other_search = SavedSearch.objects.create(
            user=other_user,
            search_type=SavedSearch.SearchType.COMPANY,
            keywords="UBS",
            city="Zurich",
            country="Switzerland",
        )
        self._make_job("search-other-user", matched_search="UBS")

        results = list_jobs(self.user, "main", search_ids=[str(other_search.pk)])

        self.assertEqual(list(results), [])

    def test_search_filter_combines_in_and_with_score_and_status(self):
        match = self._make_job(
            "search-and-match", matched_search="UBS", score=5, status=Job.Status.NEW
        )
        self._make_job("search-and-wrong-score", matched_search="UBS", score=3, status=Job.Status.NEW)
        wrong_search = self._make_job(
            "search-and-wrong-search", matched_search="Deloitte", score=5, status=Job.Status.NEW
        )

        results = list_jobs(
            self.user, "main", scores=[5], statuses=[Job.Status.NEW], search_ids=["none"]
        )
        # Nessuno dei tre ha matched_search vuoto: il filtro "none" combinato
        # in AND con score/stato deve restituire l'insieme vuoto, non
        # ignorare gli altri filtri né ignorare se stesso.
        self.assertEqual(list(results), [])

        results = list_jobs(
            self.user,
            "main",
            scores=[5],
            statuses=[Job.Status.NEW],
            search_ids=None,
        )
        # Senza filtro ricerca, contano solo score/stato: entrambi i job con
        # score 5 e stato "new" devono uscire, indipendentemente dalla loro
        # ricerca di provenienza.
        self.assertEqual({job.pk for job in results}, {match.pk, wrong_search.pk})

    def test_location_filter_combines_in_and_with_score_and_status(self):
        match = self._make_job(
            "loc-match", location="Milano, Italia", score=5, status=Job.Status.NEW
        )
        self._make_job("loc-wrong-score", location="Milano, Italia", score=3, status=Job.Status.NEW)
        self._make_job("loc-wrong-city", location="Roma, Italia", score=5, status=Job.Status.NEW)

        results = list_jobs(self.user, "main", scores=[5], statuses=[Job.Status.NEW], location="Milano")

        self.assertEqual({job.pk for job in results}, {match.pk})

    def test_location_filter_is_case_insensitive_substring_match(self):
        match = self._make_job("loc-case-match", location="Roma, Italia")
        self._make_job("loc-case-other", location="Milano, Italia")

        results = list_jobs(self.user, "main", location="roma")

        self.assertEqual({job.pk for job in results}, {match.pk})

    def test_location_filter_is_ignored_when_text_search_is_active(self):
        milano_job = self._make_job(
            "loc-query-milano", location="Milano, Italia", title="Rare Keyword Match"
        )
        roma_job = self._make_job(
            "loc-query-roma", location="Roma, Italia", title="Rare Keyword Match"
        )

        results = list_jobs(self.user, "main", query="Rare Keyword", location="Milano")

        # Come score/stato/data, anche il filtro location viene ignorato
        # quando la ricerca testuale principale è attiva.
        self.assertEqual({job.pk for job in results}, {milano_job.pk, roma_job.pk})

    def test_applicants_filter_under_25_matches_bucket_and_exact_count(self):
        bucket_job = self._make_job("app-bucket")
        Job.objects.filter(pk=bucket_job.pk).update(applicants_bucket="under_25")
        exact_job = self._make_job("app-exact")
        Job.objects.filter(pk=exact_job.pk).update(applicants_count=10)
        outside_job = self._make_job("app-outside")
        Job.objects.filter(pk=outside_job.pk).update(applicants_count=30)

        results = list_jobs(self.user, "main", applicants_ranges=["under_25"])

        self.assertEqual({job.pk for job in results}, {bucket_job.pk, exact_job.pk})

    def test_applicants_filter_over_200_matches_bucket_and_exact_count(self):
        bucket_job = self._make_job("app-bucket-over")
        Job.objects.filter(pk=bucket_job.pk).update(applicants_bucket="over_200")
        exact_job = self._make_job("app-exact-over")
        Job.objects.filter(pk=exact_job.pk).update(applicants_count=250)
        outside_job = self._make_job("app-outside-over")
        Job.objects.filter(pk=outside_job.pk).update(applicants_count=100)

        results = list_jobs(self.user, "main", applicants_ranges=["over_200"])

        self.assertEqual({job.pk for job in results}, {bucket_job.pk, exact_job.pk})

    def test_applicants_filter_middle_range_matches_only_exact_counts_in_range(self):
        in_range = self._make_job("app-mid-in")
        Job.objects.filter(pk=in_range.pk).update(applicants_count=75)
        below = self._make_job("app-mid-below")
        Job.objects.filter(pk=below.pk).update(applicants_count=20)
        above = self._make_job("app-mid-above")
        Job.objects.filter(pk=above.pk).update(applicants_count=150)

        results = list_jobs(self.user, "main", applicants_ranges=["51_100"])

        self.assertEqual({job.pk for job in results}, {in_range.pk})

    def test_applicants_filter_combines_multiple_ranges_with_or(self):
        low = self._make_job("app-multi-low")
        Job.objects.filter(pk=low.pk).update(applicants_bucket="under_25")
        high = self._make_job("app-multi-high")
        Job.objects.filter(pk=high.pk).update(applicants_bucket="over_200")
        middle = self._make_job("app-multi-middle")
        Job.objects.filter(pk=middle.pk).update(applicants_count=75)

        results = list_jobs(self.user, "main", applicants_ranges=["under_25", "over_200"])

        self.assertEqual({job.pk for job in results}, {low.pk, high.pk})

    def test_recruiter_filter_yes_and_no(self):
        with_recruiter = self._make_job("rec-yes")
        Job.objects.filter(pk=with_recruiter.pk).update(recruiter_name="Jane Doe")
        without_recruiter = self._make_job("rec-no")

        yes_results = list_jobs(self.user, "main", has_recruiter=True)
        no_results = list_jobs(self.user, "main", has_recruiter=False)

        self.assertEqual({job.pk for job in yes_results}, {with_recruiter.pk})
        self.assertEqual({job.pk for job in no_results}, {without_recruiter.pk})

    def test_applicants_and_recruiter_filters_are_ignored_when_text_search_is_active(self):
        job_a = self._make_job("app-rec-query-a", title="Rare Keyword Match")
        Job.objects.filter(pk=job_a.pk).update(applicants_bucket="under_25", recruiter_name="Jane Doe")
        job_b = self._make_job("app-rec-query-b", title="Rare Keyword Match")

        results = list_jobs(
            self.user,
            "main",
            query="Rare Keyword",
            applicants_ranges=["over_200"],
            has_recruiter=True,
        )

        self.assertEqual({job.pk for job in results}, {job_a.pk, job_b.pk})


class ArchiveJobApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="archive@example.com", email="archive@example.com", password="pw-Archive-12345!"
        )
        self.job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            status=Job.Status.CV_GENERATED,
        )
        self.client.force_authenticate(self.user)

    def test_archive_sets_is_archived_true(self):
        response = self.client.post(f"/api/jobs/{self.job.pk}/archive/")

        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertTrue(self.job.is_archived)

    def test_unarchive_undoes_an_archive_swipe(self):
        self.client.post(f"/api/jobs/{self.job.pk}/archive/")

        response = self.client.post(f"/api/jobs/{self.job.pk}/unarchive/")

        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_archived)

    def test_unarchive_from_archive_section_keeps_previous_status(self):
        self.job.is_archived = True
        self.job.save(update_fields=["is_archived"])

        response = self.client.post(f"/api/jobs/{self.job.pk}/unarchive/")

        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_archived)
        self.assertEqual(self.job.status, Job.Status.CV_GENERATED)


class FavoriteJobApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="favorite@example.com", email="favorite@example.com", password="pw-Favorite-12345!"
        )
        self.job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
        )
        self.client.force_authenticate(self.user)

    def test_favorite_sets_is_favorite_true(self):
        response = self.client.post(f"/api/jobs/{self.job.pk}/favorite/")

        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertTrue(self.job.is_favorite)

    def test_unfavorite_sets_is_favorite_false(self):
        self.client.post(f"/api/jobs/{self.job.pk}/favorite/")

        response = self.client.post(f"/api/jobs/{self.job.pk}/unfavorite/")

        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_favorite)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class JobDetailApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="detail@example.com", email="detail@example.com", password="pw-Detail-12345!"
        )
        self.other_user = User.objects.create_user(
            username="other-detail@example.com",
            email="other-detail@example.com",
            password="pw-Other-12345!",
        )
        self.job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            status=Job.Status.NEW,
        )
        self.client.force_authenticate(self.user)

    def test_returns_job_detail(self):
        response = self.client.get(f"/api/jobs/{self.job.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.job.pk)
        self.assertEqual(response.data["title"], "Project Manager")

    def test_another_users_job_is_not_found(self):
        self.client.force_authenticate(self.other_user)

        response = self.client.get(f"/api/jobs/{self.job.pk}/")

        self.assertEqual(response.status_code, 404)

    def test_cv_pdf_url_is_null_without_a_generated_cv(self):
        response = self.client.get(f"/api/jobs/{self.job.pk}/")

        self.assertIsNone(response.data["cv_pdf_url"])

    def test_cv_pdf_url_points_to_the_latest_cv_document(self):
        from django.core.files.base import ContentFile

        older = CVDocument.objects.create(
            job=self.job, user=self.user, html_source="<html></html>", generation_type="manual"
        )
        older.pdf_file.save("older.pdf", ContentFile(b"%PDF-1.4 older"), save=True)
        newer = CVDocument.objects.create(
            job=self.job, user=self.user, html_source="<html></html>", generation_type="manual"
        )
        newer.pdf_file.save("newer.pdf", ContentFile(b"%PDF-1.4 newer"), save=True)

        response = self.client.get(f"/api/jobs/{self.job.pk}/")

        self.assertIn("newer", response.data["cv_pdf_url"])


class MarkApplicationDoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="apply@example.com",
            email="apply@example.com",
            password="pw-Apply-12345!",
        )
        self.user.last_activity_reset = timezone.now() - timedelta(days=5)
        self.user.save(update_fields=["last_activity_reset"])

    def _make_job(self, status):
        return Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            status=status,
        )

    def test_marking_a_cv_generated_job_succeeds(self):
        job = self._make_job(Job.Status.CV_GENERATED)

        result = mark_application_done(job)

        self.assertEqual(result.status, Job.Status.APPLICATION_DONE)
        self.assertIsNotNone(result.date_application_done)

    def test_marking_a_new_job_without_cv_succeeds(self):
        job = self._make_job(Job.Status.NEW)

        result = mark_application_done(job)

        self.assertEqual(result.status, Job.Status.APPLICATION_DONE)
        self.assertIsNotNone(result.date_application_done)

    def test_marking_an_already_done_job_is_rejected(self):
        job = self._make_job(Job.Status.APPLICATION_DONE)

        with self.assertRaises(ApplicationMarkRejected):
            mark_application_done(job)

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.APPLICATION_DONE)

    def test_marking_resets_user_inactivity_timer(self):
        job = self._make_job(Job.Status.CV_GENERATED)
        previous_reset = self.user.last_activity_reset

        mark_application_done(job)

        self.user.refresh_from_db()
        self.assertGreater(self.user.last_activity_reset, previous_reset)


class MarkApplicationDoneApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="applyapi@example.com",
            email="applyapi@example.com",
            password="pw-ApplyApi-12345!",
        )
        self.client.force_authenticate(self.user)

    def _make_job(self, status):
        return Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            status=status,
        )

    def test_endpoint_marks_job_done(self):
        job = self._make_job(Job.Status.CV_GENERATED)

        response = self.client.post(f"/api/jobs/{job.pk}/mark-application-done/")

        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.APPLICATION_DONE)

    def test_endpoint_marks_a_new_job_without_cv_done(self):
        job = self._make_job(Job.Status.NEW)

        response = self.client.post(f"/api/jobs/{job.pk}/mark-application-done/")

        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.APPLICATION_DONE)

    def test_endpoint_rejects_an_already_done_job(self):
        job = self._make_job(Job.Status.APPLICATION_DONE)

        response = self.client.post(f"/api/jobs/{job.pk}/mark-application-done/")

        self.assertEqual(response.status_code, 409)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.APPLICATION_DONE)


class SeedE2eJobsCommandTests(TestCase):
    """Il comando `seed_e2e_jobs` (Sprint 19) crea i fixture usati dai test
    e2e Playwright del frontend — verificato qui solo per non lasciare senza
    copertura un comando che scrive dati, non perché la UI lo usi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="e2e-seed@example.com", email="e2e-seed@example.com", password="pw-Seed-12345!"
        )

    @override_settings(DEBUG=True)
    def test_creates_the_expected_jobs(self):
        from io import StringIO

        from django.core.management import call_command

        call_command("seed_e2e_jobs", "e2e-seed@example.com", stdout=StringIO())

        jobs = Job.objects.filter(user=self.user, external_id__startswith="e2e-")
        self.assertEqual(jobs.count(), 6)
        self.assertTrue(jobs.filter(is_archived=True).exists())
        self.assertTrue(jobs.filter(origin=Job.Origin.IMPORTED).exists())

    @override_settings(DEBUG=True)
    def test_is_idempotent(self):
        from io import StringIO

        from django.core.management import call_command

        call_command("seed_e2e_jobs", "e2e-seed@example.com", stdout=StringIO())
        call_command("seed_e2e_jobs", "e2e-seed@example.com", stdout=StringIO())

        self.assertEqual(Job.objects.filter(user=self.user, external_id__startswith="e2e-").count(), 6)

    @override_settings(DEBUG=False)
    def test_refuses_to_run_without_debug(self):
        from io import StringIO

        from django.core.management import CommandError, call_command

        with self.assertRaises(CommandError):
            call_command("seed_e2e_jobs", "e2e-seed@example.com", stdout=StringIO())


class GenerateReferralMessageApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="referral-api@example.com",
            email="referral-api@example.com",
            password="pw-ReferralApi-12345!",
            plan=User.Plan.PRO,
        )
        Profile.objects.create(user=self.user)
        self.job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-referral-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione della posizione.",
            apply_url="https://linkedin.com/jobs/view/1",
        )
        self.client.force_authenticate(self.user)

    def test_generates_a_message_and_returns_its_content(self):
        fake_content = {"subject": "", "message": "Ciao Mario, ..."}
        with patch(
            "apps.cv.referral_message_generation.generate_referral_message_content",
            return_value=fake_content,
        ):
            response = self.client.post(
                f"/api/jobs/{self.job.pk}/generate-referral-message/",
                {"channel": "linkedin", "recipient_name": "Mario"},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["content"], "Ciao Mario, ...")
        self.assertEqual(response.data["channel"], "linkedin")
        self.assertEqual(response.data["recipient_name"], "Mario")

    def test_invalid_channel_is_rejected_with_400(self):
        response = self.client.post(
            f"/api/jobs/{self.job.pk}/generate-referral-message/",
            {"channel": "whatsapp"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_history_endpoint_returns_all_messages_most_recent_first(self):
        fake_content = {"subject": "Oggetto", "message": "Corpo"}
        with patch(
            "apps.cv.referral_message_generation.generate_referral_message_content",
            return_value=fake_content,
        ):
            self.client.post(
                f"/api/jobs/{self.job.pk}/generate-referral-message/",
                {"channel": "linkedin", "recipient_name": "Mario"},
                format="json",
            )
            self.client.post(
                f"/api/jobs/{self.job.pk}/generate-referral-message/",
                {"channel": "email", "recipient_name": "Giulia"},
                format="json",
            )

        response = self.client.get(f"/api/jobs/{self.job.pk}/referral-messages/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["recipient_name"], "Giulia")
        self.assertEqual(response.data[1]["recipient_name"], "Mario")

    def test_instructions_endpoint_returns_recent_instructions(self):
        fake_content = {"subject": "", "message": "Corpo"}
        with patch(
            "apps.cv.referral_message_generation.generate_referral_message_content",
            return_value=fake_content,
        ):
            self.client.post(
                f"/api/jobs/{self.job.pk}/generate-referral-message/",
                {"channel": "linkedin", "instructions": "Collega ex, team design"},
                format="json",
            )

        response = self.client.get("/api/referral-message-instructions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["instructions"], ["Collega ex, team design"])
