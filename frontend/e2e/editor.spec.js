import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'

// Editor di CV e cover letter (Sprint 76). Senza chiave AI in questo
// ambiente non si possono generare documenti: il test crea nel DB di prova
// un CV e una cover letter "modificabili" (content_json) e una cronologia
// della chat con una proposta, poi usa le pagine come un utente.

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_DIR = path.resolve(__dirname, '../../backend')
const INVITE_CODE = process.env.E2E_INVITE_CODE || ''
const PYTHON_ENV = {
  ...process.env,
  DJANGO_SECRET_KEY: 'dev-insecure-secret-key',
  DJANGO_DEBUG: 'true',
  DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
  POSTGRES_HOST: 'localhost',
}

function djangoShell(code) {
  return execFileSync('.venv/bin/python', ['manage.py', 'shell'], { cwd: BACKEND_DIR, env: PYTHON_ENV, input: code }).toString()
}

const SETUP = `
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from apps.jobs.models import Job
from apps.cv.models import CVDocument, CoverLetterDocument
from apps.profiles.models import Profile, Skill, Certification
u = get_user_model().objects.get(email="__EMAIL__")
u.extra_credit = Decimal("__CREDIT__"); u.save(update_fields=["extra_credit"])
profile, _ = Profile.objects.get_or_create(user=u)
for name in ["Python", "Project management", "Stakeholder management"]:
    Skill.objects.create(profile=profile, name=name)
Certification.objects.create(profile=profile, name="PMP")
job = Job.objects.create(user=u, external_id="e2e-editor", title="Senior Product Manager", company="Esempio Srl", location="Milano", description="Descrizione di prova.", score=8, score_match=[], score_gaps=[], score_reasoning="", status="cv_generated", origin="collected")
bullets = [{"id": f"b{i}", "text": f"Risultato **misurabile** numero {i} ottenuto nel ruolo.", "shown": True} for i in range(1, 4)]
cv = {
  "summary": "Product manager con 8 anni di esperienza nel guidare prodotti digitali dalla scoperta al lancio.",
  "qualification": "Senior Product Manager",
  "translated_city": "Milano", "content_language": "it",
  "areas_of_expertise": ["Product discovery", "Roadmap", "Analisi dati"],
  "experiences": [
    {"profile_experience_id": 9001, "company": "Esempio Energia S.p.A.", "role": "Sales Manager - B2B", "location": "Roma, IT", "dates": "2026 - Presente", "technologies": [], "shown": True, "bullets": bullets},
    {"profile_experience_id": 9002, "company": "Studio Esempio", "role": "Business Analyst", "location": "Milano, IT", "dates": "2020 - 2025", "technologies": [], "shown": True, "bullets": [{"id": "c1", "text": "Analisi dei processi.", "shown": True}]},
  ],
  "educations": [{"institution": "Politecnico di Milano", "title": "Laurea in Ingegneria", "location": "Milano", "dates": "2014 - 2019", "notes": ""}],
  "skills": ["Python"], "certifications": [], "languages": [{"language": "en", "level": "fluent"}],
}
CVDocument.objects.create(job=job, user=u, html_source="", pdf_file=ContentFile(b"%PDF-1.4 test", name="cv.pdf"), generation_type="manual", content_json=cv, page_count=1)
paragraphs = [{"id": f"p{i}", "text": f"Testo del paragrafo {i} della lettera."} for i in range(1, 5)]
CoverLetterDocument.objects.create(job=job, user=u, html_source="", pdf_file=ContentFile(b"%PDF-1.4 test", name="cl.pdf"), content_json={"content_language": "it", "translated_city": "Milano", "paragraphs": paragraphs}, page_count=1)
print("JOB", job.id)
`

// Cronologia della chat con una proposta sul sommario (dopo l'apertura
// della bozza, che la azzera).
const CHAT = `
from apps.cv.models import CVDraft
d = CVDraft.objects.get(job_id=__JOB__)
d.chat_history = [
  {"role": "user", "message": "Rendi il sommario più sintetico"},
  {"role": "assistant", "message": "Ecco una proposta.", "actions": [{"type": "update_summary", "text": "Product manager con 8 anni di esperienza su prodotti digitali."}]},
]
d.save(update_fields=["chat_history"])
print("OK")
`

const NEWER_CV = `
from django.core.files.base import ContentFile
from apps.cv.models import CVDocument
latest = CVDocument.objects.filter(job_id=__JOB__).latest("generated_at")
CVDocument.objects.create(job=latest.job, user=latest.user, html_source="", pdf_file=ContentFile(b"%PDF-1.4 test", name="cv2.pdf"), generation_type="manual", content_json=latest.content_json, page_count=1)
print("OK")
`

let suffix = 0
async function setupEditorUser(page, request, baseURL, { credit = '4.60' } = {}) {
  suffix += 1
  const email = `e2e-editor-${Date.now()}-${suffix}@example.com`
  const password = 'SuperSecret123!'
  await request.post(`${baseURL}/api/accounts/register/`, {
    data: { email, password, invite_code: INVITE_CODE, accept_privacy: true, accept_terms: true, confirm_age: true },
  })
  const jobId = djangoShell(SETUP.replace('__EMAIL__', email).replace('__CREDIT__', credit)).match(/JOB (\d+)/)[1]
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()
  await page.waitForURL(/onboarding|list/)
  return jobId
}

async function openCvEditor(page, jobId) {
  await page.goto(`/jobs/${jobId}/cv-editor`)
  await expect(page.getByRole('heading', { name: 'Modifica CV', level: 1 })).toBeVisible()
}

test.describe('editor su mobile', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('editor del CV: fisarmoniche, interruttore, punti elenco, anteprima e barra azione', async ({ page, request, baseURL }) => {
    const jobId = await setupEditorUser(page, request, baseURL)
    await openCvEditor(page, jobId)

    // La barra azione sostituisce la barra di tab.
    await expect(page.getByRole('navigation', { name: 'Navigazione principale' })).not.toBeVisible()
    const bar = page.getByTestId('action-bar')
    await expect(bar.getByRole('button', { name: 'Assistente' })).toBeVisible()
    await expect(bar.getByRole('button', { name: 'Genera PDF finale' })).toBeVisible()

    // Sommario aperto, le altre sezioni chiuse con il riassunto.
    await expect(page.getByRole('button', { name: 'Sommario' })).toHaveAttribute('aria-expanded', 'true')
    const experiences = page.getByRole('button', { name: /^Esperienze/ })
    await expect(experiences).toHaveAttribute('aria-expanded', 'false')
    await expect(experiences).toContainText('2 aziende')
    await experiences.click()
    await page.getByRole('button', { name: /^Esempio Energia S\.p\.A\./ }).click()

    // "Mostra nel CV" è un interruttore (prima una checkbox), stesso dato.
    const shown = page.getByRole('switch')
    await expect(shown).toHaveAttribute('aria-checked', 'true')
    await shown.click()
    await expect(shown).toHaveAttribute('aria-checked', 'false')

    await expect(page.getByRole('checkbox', { name: 'Visibile' })).toHaveCount(3)
    await page.getByRole('button', { name: 'Aggiungi punto' }).click()
    await expect(page.getByRole('checkbox', { name: 'Visibile' })).toHaveCount(4)
    await expect(page.getByText('Salvato')).toBeVisible({ timeout: 10000 })

    // Anteprima: stesso meccanismo (PDF del server in un iframe) o avviso.
    await page.getByText('Anteprima', { exact: true }).click()
    // Sprint 83: il Chromium headless dei test non ha un visualizzatore PDF
    // (pdfViewerEnabled false): qui compare l'avviso al posto dell'iframe.
    await expect(
      page.getByTitle('Anteprima del CV').or(page.getByText('Anteprima non disponibile al momento.')).or(page.getByTestId('preview-no-viewer')),
    ).toBeVisible({
      timeout: 20000,
    })
    await page.getByText('Modifica', { exact: true }).click()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  })

  test('assistente: proposta accettata, prezzo e saldo dall’API, contesto dai punti elenco', async ({ page, request, baseURL }) => {
    const jobId = await setupEditorUser(page, request, baseURL)
    await openCvEditor(page, jobId)
    djangoShell(CHAT.replace('__JOB__', jobId))
    await page.reload()
    await expect(page.getByRole('heading', { name: 'Modifica CV', level: 1 })).toBeVisible()

    // Un punto elenco come contesto (Sprint 61), poi il pannello dal basso.
    await page.getByRole('button', { name: /^Esperienze/ }).click()
    await page.getByRole('button', { name: /^Esempio Energia S\.p\.A\./ }).click()
    await page.getByRole('button', { name: 'Usa come contesto per la chat AI' }).first().click()
    await page.getByTestId('action-bar').getByRole('button', { name: 'Assistente' }).click()

    const sheet = page.getByRole('dialog', { name: 'Assistente bozza' })
    await expect(sheet.getByText('Ogni messaggio costa')).toContainText('4,60')
    await expect(sheet.getByText('Contenuto generato con l’AI: verificalo prima di usarlo.')).toBeVisible()
    await expect(sheet.getByRole('button', { name: /^Togli dal contesto/ })).toBeVisible()
    await sheet.getByRole('button', { name: 'Accetta' }).click()
    await expect(sheet.getByText('Applicata')).toBeVisible()
    await sheet.getByRole('button', { name: 'Chiudi' }).click()
    await expect(page.getByTestId('cv-section-summary')).toContainText('Product manager con 8 anni di esperienza su prodotti digitali.')

    // Riaperto, la decisione resta (stato nella pagina e sul server).
    await page.getByTestId('action-bar').getByRole('button', { name: 'Assistente' }).click()
    await expect(sheet.getByText('Applicata')).toBeVisible()
  })

  test('assistente con credito insufficiente: campo e invio disattivati con il motivo', async ({ page, request, baseURL }) => {
    const jobId = await setupEditorUser(page, request, baseURL, { credit: '0.00' })
    await openCvEditor(page, jobId)
    await page.getByTestId('action-bar').getByRole('button', { name: 'Assistente' }).click()
    const sheet = page.getByRole('dialog', { name: 'Assistente bozza' })
    await expect(sheet.getByTestId('chat-credit-blocked')).toHaveText('Saldo credito insufficiente per inviare un altro messaggio.')
    await expect(sheet.getByRole('textbox')).toBeDisabled()
    await expect(sheet.getByRole('button', { name: 'Invia' })).toBeDisabled()
  })

  test('bozza superata: finestra con "Riparti" e "Continua la bozza"', async ({ page, request, baseURL }) => {
    const jobId = await setupEditorUser(page, request, baseURL)
    await openCvEditor(page, jobId)
    djangoShell(NEWER_CV.replace('__JOB__', jobId))
    await page.reload()
    const modal = page.getByRole('dialog', { name: 'C’è un CV più recente della bozza' })
    await expect(modal.getByRole('button', { name: 'Riparti dal nuovo CV' })).toBeVisible()
    await modal.getByRole('button', { name: 'Continua la bozza' }).click()
    await expect(page.getByRole('heading', { name: 'Modifica CV', level: 1 })).toBeVisible()
  })
})

test('desktop: cover letter con la chat in colonna accanto all’editor', async ({ page, request, baseURL }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  const jobId = await setupEditorUser(page, request, baseURL)
  await page.goto(`/jobs/${jobId}/cover-letter-editor`)
  await expect(page.getByRole('heading', { name: 'Modifica Cover Letter', level: 1 })).toBeVisible()

  // Chat fissa a destra (nessun pulsante "Assistente" da 1024 px).
  const aside = page.getByRole('complementary', { name: 'Assistente cover letter' })
  await expect(aside).toBeVisible()
  await expect(aside.getByText('Ogni messaggio costa')).toBeVisible()
  await expect(page.getByTestId('action-bar').getByRole('button', { name: 'Assistente' })).not.toBeVisible()
  const box = await aside.boundingBox()
  expect(Math.round(box.width)).toBe(400)

  await expect(page.getByTestId('cover-letter-paragraph')).toHaveCount(4)
  await expect(page.getByText('Paragrafo 1 · Apertura')).toBeVisible()
  await expect(page.getByText('Paragrafo 4 · Chiusura')).toBeVisible()
  await expect(page.getByLabel('Paragrafo 2', { exact: true })).toHaveAttribute('maxlength', '3000')
  await page.getByRole('button', { name: 'Aggiungi paragrafo' }).click()
  await expect(page.getByTestId('cover-letter-paragraph')).toHaveCount(5)
  await page.getByRole('button', { name: 'Rimuovi paragrafo' }).last().click()
  await expect(page.getByTestId('cover-letter-paragraph')).toHaveCount(4)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1280)
})

// Sprint 83: browser senza visualizzatore PDF incorporato (Chrome per
// Android, navigator.pdfViewerEnabled === false): avviso al posto dell'iframe.
test.describe('anteprima senza visualizzatore PDF', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('mostra l’avviso invece dell’iframe', async ({ page, request, baseURL }) => {
    await page.addInitScript(() => {
      Object.defineProperty(Navigator.prototype, 'pdfViewerEnabled', { get: () => false, configurable: true })
    })
    const jobId = await setupEditorUser(page, request, baseURL)
    await openCvEditor(page, jobId)
    await page.getByText('Anteprima', { exact: true }).click()
    await expect(page.getByTestId('preview-no-viewer')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('preview-no-viewer')).toContainText('non è disponibile in questo browser')
    await expect(page.getByTitle('Anteprima del CV')).toHaveCount(0)
  })

  test('con il visualizzatore PDF resta l’iframe', async ({ page, request, baseURL }) => {
    await page.addInitScript(() => {
      Object.defineProperty(Navigator.prototype, 'pdfViewerEnabled', { get: () => true, configurable: true })
    })
    const jobId = await setupEditorUser(page, request, baseURL)
    await openCvEditor(page, jobId)
    await page.getByText('Anteprima', { exact: true }).click()
    await expect(page.getByTitle('Anteprima del CV').or(page.getByText('Anteprima non disponibile al momento.'))).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('preview-no-viewer')).toHaveCount(0)
  })
})
