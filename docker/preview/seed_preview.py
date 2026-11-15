# Dati finti dell'anteprima (eseguito con: python manage.py shell < seed_preview.py
# dentro preview-web). Idempotente: se l'utente di prova esiste lo ricrea da zero.
# Credenziali da variabili d'ambiente (.env.preview), mai scritte qui.
import datetime
import os
from decimal import Decimal

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.legal import record_acceptances
from apps.accounts.models import User
from apps.cv.models import CoverLetterDocument, CVDocument, ReferralMessageDocument
from apps.jobs.management.commands.seed_e2e_jobs import SEED_JOBS
from apps.jobs.models import Job
from apps.profiles.models import Certification, Education, Experience, Language, Profile, Skill

email = os.environ["PREVIEW_APP_EMAIL"]
password = os.environ["PREVIEW_APP_PASSWORD"]
User.objects.filter(email=email).delete()
user = User.objects.create_user(username=email, email=email, password=password)
user.plan = User.Plan.PRO
user.extra_credit = Decimal("4.60")
user.email_verified = True
user.save()
record_acceptances(user)

profile, _ = Profile.objects.get_or_create(user=user)
profile.summary = "Product manager con esperienza in prodotti digitali (profilo di prova)."
profile.city, profile.country_code, profile.phone = "Milano", "IT", "+39 000 0000000"
profile.save()
Experience.objects.create(profile=profile, company="Esempio Energia S.p.A.", role="Sales Manager - B2B", location="Roma",
                          start_date=datetime.date(2022, 1, 1), bullets=["Gestione di clienti business."])
Education.objects.create(profile=profile, institution="Università di Esempio", title="Laurea in Economia", location="Milano",
                         start_date=datetime.date(2014, 9, 1), end_date=datetime.date(2019, 7, 1))
for name in ["Project management", "Analisi dati", "Negoziazione"]:
    Skill.objects.create(profile=profile, name=name)
Certification.objects.create(profile=profile, name="Certificazione di esempio")
Language.objects.create(profile=profile, language="en", level="fluent")

now = timezone.now()
jobs = []
for data in SEED_JOBS:
    job = Job.objects.create(user=user, source=Job.Source.LINKEDIN, date_scored=now, **data)
    Job.objects.filter(pk=job.pk).update(date_collected=now)
    jobs.append(job)

# Un job con documenti modificabili negli editor e un messaggio di networking.
job = next(j for j in jobs if not j.is_archived)
cv_content = {
    "summary": "Product manager con 8 anni di esperienza nel guidare prodotti digitali dalla scoperta al lancio.",
    "qualification": "Senior Product Manager",
    "translated_city": "Milano", "content_language": "it",
    "areas_of_expertise": ["Product discovery", "Roadmap", "Analisi dati"],
    "experiences": [{
        "profile_experience_id": profile.experiences.first().id, "company": "Esempio Energia S.p.A.",
        "role": "Sales Manager - B2B", "location": "Roma, IT", "dates": "2022 - Presente", "technologies": [], "shown": True,
        "bullets": [{"id": f"b{i}", "text": f"Risultato **misurabile** numero {i}.", "shown": True} for i in range(1, 4)],
    }],
    "educations": [{"institution": "Università di Esempio", "title": "Laurea in Economia", "location": "Milano", "dates": "2014 - 2019", "notes": ""}],
    "skills": ["Project management"], "certifications": [], "languages": [{"language": "en", "level": "fluent"}],
}
CVDocument.objects.create(job=job, user=user, html_source="", pdf_file=ContentFile(b"%PDF-1.4 anteprima", name="cv.pdf"),
                          generation_type="manual", content_json=cv_content, page_count=1)
CoverLetterDocument.objects.create(job=job, user=user, html_source="", pdf_file=ContentFile(b"%PDF-1.4 anteprima", name="cl.pdf"),
                                   content_json={"content_language": "it", "translated_city": "Milano",
                                                 "paragraphs": [{"id": f"p{i}", "text": f"Testo del paragrafo {i}."} for i in range(1, 5)]},
                                   page_count=1, instructions_used="Tono più diretto")
ReferralMessageDocument.objects.create(job=job, user=user, channel="linkedin", recipient_name="Persona di prova",
                                       content="Ciao, ti scrivo per l'offerta di lavoro: ti andrebbe di presentarmi al team?")
Job.objects.filter(pk=job.pk).update(status=Job.Status.CV_GENERATED)
print("seed anteprima: ok,", len(jobs), "job")
