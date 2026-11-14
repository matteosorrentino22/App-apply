from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils.dateparse import parse_datetime

from apps.jobs.models import Job

# Momento del passaggio dalla scala 1-5 alla 1-10 (Sprint 47). Il commit
# d0faa0d è del 2026-09-28 14:39 UTC, ma il codice era già in produzione dal
# 2026-09-24 sera: sui dati l'ultimo punteggio 1-5 è delle 08:37 UTC del
# 24/09 e il primo su 1-10 (un 6) delle 21:07 UTC dello stesso giorno, con
# nessuno scoring in mezzo (migrazione jobs/0011 applicata alle 21:10 UTC).
# Usare la data del commit avrebbe raddoppiato circa mille punteggi già su
# 1-10. Verificato sul dump del 2026-11-14 (Sprint 68).
LEGACY_SCALE_CUTOFF = datetime(2026, 9, 24, 21, 0, tzinfo=dt_timezone.utc)


class Command(BaseCommand):
    help = (
        "Riscala x2 i punteggi su scala 1-5 (job scorati prima dello Sprint 47) e li marca con "
        "score_rescaled_from_legacy. Idempotente. Di default è un dry-run: con --confirm applica."
    )

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true", help="Applica la riscalatura.")
        parser.add_argument(
            "--before",
            help=f"Data/ora ISO di taglio (default {LEGACY_SCALE_CUTOFF.isoformat()}).",
        )

    def handle(self, *args, confirm=False, before=None, **options):
        cutoff = LEGACY_SCALE_CUTOFF
        if before:
            cutoff = parse_datetime(before)
            if cutoff is None or cutoff.tzinfo is None:
                raise CommandError("--before deve essere una data/ora ISO con fuso, es. 2026-09-24T21:00:00+00:00")

        legacy = Job.objects.filter(
            score__isnull=False, date_scored__lt=cutoff, score_rescaled_from_legacy=False
        )
        anomalous = legacy.filter(score__gt=5)
        to_rescale = legacy.filter(score__lte=5)

        self.stdout.write(f"Taglio: {cutoff.isoformat()}")
        self.stdout.write(
            "Già riscalati in precedenza: "
            f"{Job.objects.filter(score_rescaled_from_legacy=True).count()}"
        )
        self.stdout.write(f"Da riscalare: {to_rescale.count()}")
        for score in range(1, 6):
            self.stdout.write(f"  {score} -> {score * 2}: {to_rescale.filter(score=score).count()}")
        if anomalous.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Punteggi > 5 prima del taglio (lasciati invariati, controllare il taglio): "
                    f"{anomalous.count()}"
                )
            )

        if not confirm:
            self.stdout.write(self.style.WARNING("Dry-run: nulla è stato modificato. Usa --confirm per applicare."))
            return

        with transaction.atomic():
            updated = to_rescale.update(score=F("score") * 2, score_rescaled_from_legacy=True)
        self.stdout.write(self.style.SUCCESS(f"Riscalati {updated} punteggi."))
