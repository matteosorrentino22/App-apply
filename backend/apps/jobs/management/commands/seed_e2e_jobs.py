from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.jobs.models import Job

# Set fisso e deterministico di Job per i test e2e Playwright (Sprint 19):
# copre le tre sezioni, i tre stati filtrabili e l'intera scala di punteggio,
# così i test possono asserire su valori noti invece che sui dati reali
# della raccolta notturna (mai disponibili in questo ambiente, §3.4 tecniche
# — nessuna chiave Apify/Claude).
SEED_JOBS = [
    dict(
        external_id="e2e-1",
        title="Project Manager",
        company="Acme Srl",
        location="Milano",
        description="Gestione progetti IT cross-funzionali.",
        apply_url="https://linkedin.com/jobs/view/101",
        score=4,
        score_match=["5+ anni PM"],
        score_gaps=["Nessuna esperienza fintech"],
        score_reasoning="Ottima corrispondenza su gestione stakeholder.",
        status=Job.Status.NEW,
        origin=Job.Origin.COLLECTED,
    ),
    dict(
        external_id="e2e-2",
        title="Backend Developer",
        company="Beta SpA",
        location="Remoto",
        description="Sviluppo backend Python/Django.",
        apply_url="https://linkedin.com/jobs/view/102",
        score=2,
        score_match=["Python"],
        score_gaps=["Java/Spring richiesto"],
        score_reasoning="Sovrapposizione limitata con lo stack richiesto.",
        status=Job.Status.NEW,
        origin=Job.Origin.COLLECTED,
    ),
    dict(
        external_id="e2e-3",
        title="Head of Operations",
        company="Gamma Group",
        location="Torino",
        description="Direzione operativa multi-sede.",
        apply_url="https://linkedin.com/jobs/view/103",
        score=5,
        score_match=["Direzione operativa"],
        score_gaps=[],
        score_reasoning="Match quasi perfetto.",
        status=Job.Status.CV_GENERATED,
        origin=Job.Origin.COLLECTED,
    ),
    dict(
        external_id="e2e-4",
        title="Data Analyst",
        company="Delta srl",
        location="Bologna",
        description="Analisi dati e reportistica.",
        apply_url="https://linkedin.com/jobs/view/104",
        score=3,
        score_match=["SQL"],
        score_gaps=["Power BI"],
        score_reasoning="Buona base SQL, manca Power BI.",
        status=Job.Status.APPLICATION_DONE,
        origin=Job.Origin.COLLECTED,
    ),
    dict(
        external_id="e2e-5",
        title="Consulente HR",
        company="Epsilon spa",
        location="Roma",
        description="Selezione e sviluppo HR.",
        apply_url="https://linkedin.com/jobs/view/105",
        score=4,
        score_match=["Recruiting"],
        score_gaps=[],
        score_reasoning="Solida corrispondenza sulle competenze HR.",
        status=Job.Status.NEW,
        origin=Job.Origin.IMPORTED,
    ),
    dict(
        external_id="e2e-6",
        title="Job archiviato",
        company="Zeta srl",
        location="Napoli",
        description="Job di test già archiviato.",
        apply_url="https://linkedin.com/jobs/view/106",
        score=1,
        score_match=[],
        score_gaps=["Tutto"],
        score_reasoning="Corrispondenza molto bassa.",
        status=Job.Status.NEW,
        origin=Job.Origin.COLLECTED,
        is_archived=True,
    ),
]


class Command(BaseCommand):
    help = "Crea un set fisso di Job per i test e2e Playwright (solo con DEBUG=True)."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_e2e_jobs è disponibile solo con DEBUG=True.")

        email = options["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"Nessun utente con email {email}.") from exc

        Job.objects.filter(user=user, external_id__startswith="e2e-").delete()
        for payload in SEED_JOBS:
            Job.objects.create(user=user, source=Job.Source.LINKEDIN, date_scored=timezone.now(), **payload)

        self.stdout.write(self.style.SUCCESS(f"Creati {len(SEED_JOBS)} job di test per {email}."))
