from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    """Imposta piano e credito di un utente, simulando un'azione da Django
    Admin (Sprint 20, §3 funzionali "Gestione account": nessun checkout in
    UI, solo amministratore) — usato dai test e2e Playwright, solo con
    DEBUG=True."""

    help = "Imposta plan/extra_credit per un utente di test e2e (solo con DEBUG=True)."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)
        parser.add_argument("--plan", type=str, default=User.Plan.PRO)
        parser.add_argument("--credit", type=str, default="7.50")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("set_e2e_account è disponibile solo con DEBUG=True.")

        email = options["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"Nessun utente con email {email}.") from exc

        user.plan = options["plan"]
        user.extra_credit = Decimal(options["credit"])
        user.save(update_fields=["plan", "extra_credit"])

        self.stdout.write(self.style.SUCCESS(f"{email}: plan={user.plan} extra_credit={user.extra_credit}"))
