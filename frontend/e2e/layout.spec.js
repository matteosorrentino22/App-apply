import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'
import { findLayoutIssues, openAllSections } from './helpers/layout'

// Regressione dell'impaginazione (Sprint 81). Percorre le pagine principali
// con dati lunghi (azienda e ruolo lunghi, molti punti elenco, date
// compilate) e segnala: pagina più larga dello schermo, elementi che escono
// dalla loro card, controlli sovrapposti, contenuto coperto dalle barre in
// basso. Gira in Chromium a 360/390/1280 px (progetto `chromium`) e in
// WebKit con l'emulazione di iPhone 13 e iPhone SE (progetti `iphone-*`,
// playwright.config.js). Con LAYOUT_SHOTS=<cartella> salva anche gli
// screenshot a pagina intera.

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_DIR = path.resolve(__dirname, '../../backend')
const INVITE_CODE = process.env.E2E_INVITE_CODE || ''
const SHOTS = process.env.LAYOUT_SHOTS
const ENV = {
  ...process.env,
  DJANGO_SECRET_KEY: 'dev-insecure-secret-key',
  DJANGO_DEBUG: 'true',
  DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
  POSTGRES_HOST: 'localhost',
}
const python = (args, input) => execFileSync('.venv/bin/python', ['manage.py', ...args], { cwd: BACKEND_DIR, env: ENV, input }).toString()

const LONG_DATA = `
import datetime
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from apps.jobs.models import Job
from apps.cv.models import CVDocument, CoverLetterDocument
from apps.profiles.models import Profile, Experience, Education, Skill, Certification, Language
from apps.searches.models import SavedSearch
u = get_user_model().objects.get(email="__EMAIL__")
u.first_name = "Maria Alessandra"; u.last_name = "Bianchi-Fontanarossa"; u.plan = "pro"; u.extra_credit = Decimal("7.50")
u.save()
p, _ = Profile.objects.get_or_create(user=u)
p.summary = "Responsabile commerciale con quindici anni di esperienza nello sviluppo di mercati esteri. " * 3
p.city = "Reggio nell'Emilia"; p.country_code = "IT"; p.phone = "+39 333 123 4567"; p.email = "maria.bianchi@example.com"
p.linkedin_url = "https://www.linkedin.com/in/maria-alessandra-bianchi-fontanarossa-1234567890"; p.save()
bullets = [f"Coordinamento di un gruppo internazionale di dodici persone su progetti di trasformazione digitale, punto {i}." for i in range(1, 11)]
for company, roles in [
    ("Società Internazionale di Consulenza Strategica e Trasformazione Digitale S.p.A.", ["Responsabile Senior dello Sviluppo Commerciale Internazionale B2B", "Key Account Manager per i mercati dell'Europa centro-orientale"]),
    ("Esempio Energia", ["Analista"]),
]:
    for i, role in enumerate(roles):
        Experience.objects.create(profile=p, company=company, role=role, location="Castelnuovo di Garfagnana", location_country_code="IT",
            start_date=datetime.date(2015 + i, 3, 1), end_date=None if i == 0 else datetime.date(2020, 12, 31), bullets=bullets, technologies=["Salesforce", "SAP S/4HANA", "Microsoft Power BI"])
Education.objects.create(profile=p, institution="Università degli Studi di Milano-Bicocca, Dipartimento di Economia", title="Laurea magistrale in Economia e Gestione delle Imprese Internazionali", location="Milano", start_date=datetime.date(2008, 9, 1), end_date=datetime.date(2011, 7, 15), notes="Tesi sui mercati emergenti, 110 e lode")
Education.objects.create(profile=p, institution="Liceo", title="Diploma", location="Milano", start_date=datetime.date(2003, 9, 1), end_date=None)
for name in ["Negoziazione", "Gestione di team internazionali e distribuiti", "Analisi dei dati di vendita", "Pianificazione strategica"]:
    Skill.objects.create(profile=p, name=name)
Certification.objects.create(profile=p, name="Project Management Professional (PMP) — Project Management Institute")
Language.objects.create(profile=p, language="en", level="fluent")
Language.objects.create(profile=p, language="de", level="intermediate")
SavedSearch.objects.create(user=u, search_type="job_role", keywords="Responsabile sviluppo commerciale internazionale", city="Castelnuovo di Garfagnana", country="Italia", is_active=True)
job = Job.objects.create(user=u, external_id="layout-long", title="Responsabile Senior dello Sviluppo Commerciale Internazionale per l'Europa", company="Società Internazionale di Consulenza Strategica S.p.A.", location="Castelnuovo di Garfagnana, Toscana", description="Descrizione " * 200, score=7, score_match=[{"label": "Esperienza pluriennale nella gestione di clienti internazionali", "reason": "Quindici anni"}], score_gaps=[{"label": "Conoscenza approfondita del mercato asiatico e della lingua cinese", "reason": "Non presente"}], score_reasoning="Buona corrispondenza complessiva. " * 10, status="cv_generated", origin="collected")
cv = {"summary": p.summary, "qualification": "Responsabile Senior dello Sviluppo Commerciale", "translated_city": "Milano", "content_language": "it", "areas_of_expertise": ["Sviluppo commerciale internazionale", "Negoziazione"],
  "experiences": [{"profile_experience_id": 9001, "company": "Società Internazionale di Consulenza Strategica e Trasformazione Digitale S.p.A.", "role": "Responsabile Senior dello Sviluppo Commerciale Internazionale B2B", "location": "Castelnuovo di Garfagnana", "dates": "2015 - Presente", "technologies": [], "shown": True, "bullets": [{"id": f"b{i}", "text": b, "shown": True} for i, b in enumerate(bullets)]}],
  "educations": [{"institution": "Università degli Studi di Milano-Bicocca", "title": "Laurea magistrale", "location": "Milano", "dates": "2008 - 2011", "notes": ""}], "skills": ["Negoziazione"], "certifications": [], "languages": [{"language": "en", "level": "fluent"}]}
CVDocument.objects.create(job=job, user=u, html_source="", pdf_file=ContentFile(b"%PDF-1.4 test", name="cv.pdf"), generation_type="manual", content_json=cv, page_count=1)
CoverLetterDocument.objects.create(job=job, user=u, html_source="", pdf_file=ContentFile(b"%PDF-1.4 test", name="cl.pdf"), content_json={"content_language": "it", "translated_city": "Milano", "paragraphs": [{"id": f"p{i}", "text": "Gentile responsabile, " * 30} for i in range(1, 4)]}, page_count=1)
print("JOB", job.id)
`

let suffix = 0
async function longDataUser(page, request) {
  suffix += 1
  const email = `e2e-layout-${Date.now()}-${suffix}@example.com`
  const password = 'SuperSecret123!'
  await request.post('/api/accounts/register/', {
    data: { email, password, invite_code: INVITE_CODE, accept_privacy: true, accept_terms: true, confirm_age: true },
  })
  python(['seed_e2e_jobs', email])
  const jobId = python(['shell'], LONG_DATA.replace('__EMAIL__', email)).match(/JOB (\d+)/)[1]
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()
  await page.waitForURL(/onboarding|list/)
  return jobId
}

// Chromium: tre larghezze; WebKit: il viewport del dispositivo emulato.
function widthsFor(testInfo) {
  return testInfo.project.name === 'chromium' ? [360, 390, 1280] : [null]
}

async function check(page, testInfo, name, all) {
  await page.waitForTimeout(400)
  const width = page.viewportSize().width
  for (const issue of await findLayoutIssues(page)) all.push(`${name} @${width}: ${issue}`)
  if (SHOTS) {
    const dir = path.resolve(SHOTS)
    mkdirSync(dir, { recursive: true })
    await page.screenshot({ path: `${dir}/${testInfo.project.name}-${name}-${width}.png`, fullPage: true })
  }
}

async function eachWidth(page, testInfo, visit) {
  const all = []
  for (const width of widthsFor(testInfo)) {
    if (width) await page.setViewportSize({ width, height: width < 800 ? 800 : 900 })
    await visit(all)
  }
  expect(all, all.join('\n')).toEqual([])
}

test.describe.configure({ timeout: 240000 })

test('impaginazione: pagine di accesso', async ({ page }, testInfo) => {
  await page.route('**/api/legal/', async (route) => {
    const response = await route.fetch()
    await route.fulfill({ response, json: { ...(await response.json()), email_enabled: true } })
  })
  await eachWidth(page, testInfo, async (all) => {
    for (const [name, url] of [
      ['login', '/login'],
      ['register', '/register'],
      ['forgot', '/forgot-password'],
      ['reset', '/reset-password?uid=x&token=y'],
      ['privacy', '/privacy'],
    ]) {
      await page.goto(url)
      await page.waitForLoadState('networkidle')
      await check(page, testInfo, name, all)
    }
  })
})

test('impaginazione: Jobs, filtri, raccolta, dettaglio, job manuale', async ({ page, request }, testInfo) => {
  const jobId = await longDataUser(page, request)
  await eachWidth(page, testInfo, async (all) => {
    await page.goto('/list')
    await expect(page.locator('[data-testid="swipe-row"]').first()).toBeVisible({ timeout: 20000 })
    await check(page, testInfo, 'list', all)
    await page.getByRole('button', { name: /^Filtri/ }).click()
    await expect(page.getByRole('dialog', { name: 'Filtri' })).toBeVisible({ timeout: 20000 })
    await check(page, testInfo, 'filters', all)
    await page.keyboard.press('Escape')
    await page.getByRole('button', { name: 'Raccogli nuovi job' }).first().click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 20000 })
    await check(page, testInfo, 'collect', all)
    await page.keyboard.press('Escape')
    await page.goto('/list?section=imported')
    await page.getByRole('button', { name: 'Aggiungi manualmente' }).first().click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 20000 })
    await check(page, testInfo, 'manual-job', all)
    await page.keyboard.press('Escape')
    await page.goto(`/jobs/${jobId}`)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 20000 })
    await openAllSections(page)
    await check(page, testInfo, 'detail', all)
  })
})

test('impaginazione: editor di CV e cover letter', async ({ page, request }, testInfo) => {
  const jobId = await longDataUser(page, request)
  await eachWidth(page, testInfo, async (all) => {
    await page.goto(`/jobs/${jobId}/cv-editor`)
    await expect(page.getByRole('heading', { name: 'Modifica CV', level: 1 })).toBeVisible({ timeout: 20000 })
    await openAllSections(page)
    await check(page, testInfo, 'cv-editor', all)
    await page.goto(`/jobs/${jobId}/cover-letter-editor`)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 20000 })
    await check(page, testInfo, 'cover-editor', all)
  })
})

test('impaginazione: Profilo con tutte le sezioni aperte', async ({ page, request }, testInfo) => {
  await longDataUser(page, request)
  await eachWidth(page, testInfo, async (all) => {
    await page.goto('/profile')
    await expect(page.getByRole('heading', { name: 'Profilo', level: 1 })).toBeVisible({ timeout: 20000 })
    await openAllSections(page)
    await check(page, testInfo, 'profile', all)
    // Con una modifica compare la barra "Salva modifiche" sopra la barra di tab.
    await page.getByLabel('Sommario professionale').first().fill('Modificato')
    await check(page, testInfo, 'profile-dirty', all)
  })
})

test('impaginazione: Impostazioni e sottopagine', async ({ page, request }, testInfo) => {
  await longDataUser(page, request)
  await eachWidth(page, testInfo, async (all) => {
    for (const [name, url] of [
      ['settings', '/settings'],
      ['searches', '/settings/searches'],
      ['limits', '/settings/limits'],
      ['privacy-settings', '/settings/privacy'],
    ]) {
      await page.goto(url)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 20000 })
      await page.waitForTimeout(500)
      await check(page, testInfo, name, all)
    }
    await page.goto('/settings/searches')
    await page.getByRole('button', { name: 'Nuova ricerca' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 20000 })
    await check(page, testInfo, 'new-search', all)
    await page.keyboard.press('Escape')
  })
})

test('impaginazione: onboarding con esperienza e date', async ({ page, request }, testInfo) => {
  await longDataUser(page, request)
  await eachWidth(page, testInfo, async (all) => {
    await page.goto('/onboarding')
    await expect(page.getByLabel('Nome', { exact: true })).toBeVisible({ timeout: 20000 })
    await check(page, testInfo, 'onboarding1', all)
    await page.getByRole('button', { name: 'Avanti' }).click()
    await expect(page.getByRole('heading', { name: 'Il tuo profilo' })).toBeVisible({ timeout: 20000 })
    await page.getByRole('button', { name: 'Aggiungi azienda' }).click()
    await page.getByLabel('Azienda').last().fill('Società Internazionale di Consulenza Strategica S.p.A.')
    await page.getByLabel('Ruolo', { exact: true }).last().fill('Responsabile Senior dello Sviluppo Commerciale')
    await page.getByLabel('Data inizio').last().fill('2020-03-01')
    await page.getByLabel('Data fine').last().fill('2024-06-30')
    await check(page, testInfo, 'onboarding2', all)
  })
})
