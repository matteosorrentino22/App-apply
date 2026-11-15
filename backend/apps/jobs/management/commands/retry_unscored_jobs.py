from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.jobs.scoring import MAX_SCORING_FAILURES, score_jobs, unscored_jobs_to_retry

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Ritenta lo scoring dei job senza punteggio (Sprint 68), gli stessi che ogni raccolta "
        f"ritenta da solo fino a {MAX_SCORING_FAILURES} fallimenti per job."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Elenca i job senza chiamare l'AI.")
        parser.add_argument("--user-id", type=int, help="Solo i job di questo utente.")
        parser.add_argument(
            "--ignore-limit",
            action="store_true",
            help=f"Include anche i job arrivati a {MAX_SCORING_FAILURES} fallimenti.",
        )

    def handle(self, *args, dry_run=False, user_id=None, ignore_limit=False, **options):
        user = None
        if user_id is not None:
            user = User.objects.filter(pk=user_id).first()
            if user is None:
                raise CommandError(f"Utente {user_id} inesistente.")

        jobs = list(unscored_jobs_to_retry(user=user, ignore_limit=ignore_limit))
        self.stdout.write(f"Job senza punteggio da ritentare: {len(jobs)}")
        if dry_run or not jobs:
            for job in jobs:
                self.stdout.write(f"  job {job.pk} (utente {job.user_id}, fallimenti {job.scoring_failures})")
            return

        scored = score_jobs(jobs)
        self.stdout.write(
            self.style.SUCCESS(f"Scorati {len(scored)} su {len(jobs)} (fallimenti registrati nel RunLog).")
        )
