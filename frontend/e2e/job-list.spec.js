import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_DIR = path.resolve(__dirname, '../../backend')

function seedJobs(email) {
  execFileSync('.venv/bin/python', ['manage.py', 'seed_e2e_jobs', email], {
    cwd: BACKEND_DIR,
    env: {
      ...process.env,
      DJANGO_SECRET_KEY: 'dev-insecure-secret-key',
      DJANGO_DEBUG: 'true',
      DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
      POSTGRES_HOST: 'localhost',
    },
  })
}

let uniqueSuffix = 0
async function registerUser(request, baseURL) {
  uniqueSuffix += 1
  const email = `e2e-jobs-${Date.now()}-${uniqueSuffix}@example.com`
  const password = 'SuperSecret123!'
  const response = await request.post(`${baseURL}/api/accounts/register/`, {
    data: { email, password },
  })
  const body = await response.json()
  return { email, password, token: body.token }
}

async function loginAsSeededUser(page, request, baseURL) {
  const { email, password, token } = await registerUser(request, baseURL)
  seedJobs(email)
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()
  await page.waitForURL(/onboarding|list/)
  await page.goto('/list')
  return { email, token }
}

function cardFor(page, title) {
  return page.locator('[data-testid="swipe-row"]', { hasText: title })
}

test('sezioni: raccolti/importati/archiviati mostrano i job attesi', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  // "Raccolti": tutti i job non archiviati con origin=collected
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).toBeVisible()
  await expect(cardFor(page, 'Consulente HR')).not.toBeVisible()
  await expect(cardFor(page, 'Job archiviato')).not.toBeVisible()

  await page.getByRole('button', { name: 'Importati' }).click()
  await expect(cardFor(page, 'Consulente HR')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()

  await page.getByRole('button', { name: 'Archiviati' }).click()
  await expect(cardFor(page, 'Job archiviato')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
})

test('filtro punteggio mostra solo i job con lo score selezionato', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  // Il filtro data di default è "oggi-oggi": i job seed hanno date_collected
  // a ora, quindi restano visibili senza dover cambiare intervallo.
  await page.getByRole('button', { name: '4', exact: true }).click()

  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).not.toBeVisible()
})

test('filtro stato mostra solo i job nello stato selezionato', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await page.getByRole('button', { name: 'CV generato' }).click()

  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
})

test('la ricerca testuale ignora gli altri filtri e resta nella sezione corrente', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  // Attiva un filtro punteggio che escluderebbe "Backend Developer" (score 2)
  await page.getByRole('button', { name: '5', exact: true }).click()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()

  await page.getByPlaceholder('Cerca per titolo, azienda, località…').fill('backend')
  await page.waitForTimeout(400)

  // La ricerca ignora il filtro punteggio attivo: il job torna visibile.
  await expect(cardFor(page, 'Backend Developer')).toBeVisible()
  await expect(page.getByText('Filtri disattivati durante la ricerca testuale.')).toBeVisible()

  // Confinata alla sezione corrente: passando a "Importati" non c'è nessun risultato per "backend".
  await page.getByRole('button', { name: 'Importati' }).click()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
})

test('archiviare un job mostra l\'opzione annulla e il ripristino funziona', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  const card = cardFor(page, 'Backend Developer')
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: 'Archivia' }).click()

  await expect(card).not.toBeVisible()
  const undoButton = page.getByRole('button', { name: 'Annulla' })
  await expect(undoButton).toBeVisible()
  await undoButton.click()

  await expect(cardFor(page, 'Backend Developer')).toBeVisible()
})

test('swipe reale (drag) archivia un job', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  const card = cardFor(page, 'Project Manager')
  const box = await card.boundingBox()
  await page.mouse.move(box.x + box.width - 20, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x - 120, box.y + box.height / 2, { steps: 10 })
  await page.mouse.up()

  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
  await expect(page.getByText('Job archiviato.')).toBeVisible()
})

test('generare il CV disabilita il pulsante e mostra il caricamento', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  const card = cardFor(page, 'Project Manager')
  const generateButton = card.getByRole('button', { name: 'Genera CV' })
  await generateButton.click()

  // Durante l'attesa il pulsante è disabilitato e mostra l'indicatore.
  await expect(card.getByRole('button', { name: 'Generazione…' })).toBeDisabled()

  // Senza ANTHROPIC_API_KEY in questo ambiente la generazione fallisce lato
  // server (gestito, 502): verifichiamo che l'errore sia mostrato e che il
  // job torni allo stato "Nuovo" invece di restare bloccato — il percorso di
  // successo reale richiede una chiave Claude valida (stessa riserva già
  // documentata per import CV e generazione automatica negli sprint precedenti).
  await expect(page.getByText('Non siamo riusciti a generare il CV. Riprova.')).toBeVisible({
    timeout: 20000,
  })
  await expect(card.getByRole('button', { name: 'Genera CV' })).toBeEnabled()
})

test('apply link e "segna candidatura fatta" sono disponibili anche senza CV generato', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  // "Project Manager" è seedato con stato "new" (nessun CV generato): sia il
  // link diretto all'annuncio sia "segna candidatura fatta" devono comunque
  // essere disponibili.
  await cardFor(page, 'Project Manager').getByRole('link', { name: 'Dettagli' }).click()
  await page.waitForURL(/jobs\//)
  await expect(page.getByRole('link', { name: "Vai all'annuncio" })).toBeVisible()

  const statusBadge = page.getByTestId('job-status-badge')
  await expect(statusBadge).toHaveText('Nuovo')
  await page.getByRole('button', { name: 'Segna candidatura fatta' }).click()

  await expect(statusBadge).toHaveText('Candidatura fatta')
  await expect(page.getByRole('button', { name: 'Segna candidatura fatta' })).not.toBeVisible()
})

test('segnare la candidatura come fatta aggiorna lo stato in dettaglio', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await cardFor(page, 'Head of Operations').getByRole('link', { name: 'Dettagli' }).click()
  await page.waitForURL(/jobs\//)

  const statusBadge = page.getByTestId('job-status-badge')
  await expect(statusBadge).toHaveText('CV generato', { timeout: 15000 })
  await page.getByRole('button', { name: 'Segna candidatura fatta' }).click()

  await expect(statusBadge).toHaveText('Candidatura fatta')
  await expect(page.getByRole('button', { name: 'Segna candidatura fatta' })).not.toBeVisible()
})

test('il pulsante "espandi motivazioni" rivela la motivazione di match/gap', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  await cardFor(page, 'Project Manager').getByRole('link', { name: 'Dettagli' }).click()
  await page.waitForURL(/jobs\//)

  await expect(page.getByText('5+ anni PM')).toBeVisible()
  await expect(
    page.getByText("L'offerta richiede almeno 5 anni di esperienza in project management"),
  ).not.toBeVisible()

  await page.getByRole('button', { name: 'Espandi motivazioni' }).click()

  await expect(
    page.getByText("L'offerta richiede almeno 5 anni di esperienza in project management"),
  ).toBeVisible()
})

test('il filtro location mostra solo i job la cui località contiene il testo cercato', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  await page.getByPlaceholder('Filtra per città o paese…').fill('Torino')
  await page.waitForTimeout(400)

  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
})

test('salvare, applicare e rimuovere un filtro preferito', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  // Imposta punteggio 4 e stato "Nuovo": isola "Project Manager" (score 4,
  // nuovo) escludendo "Head of Operations" (score 5, CV generato).
  await page.getByRole('button', { name: '4', exact: true }).click()
  await page.getByRole('button', { name: 'Nuovo', exact: true }).click()
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).not.toBeVisible()

  await page.getByRole('button', { name: 'Salva filtri attuali' }).click()
  await page.getByLabel('Nome').fill('Nuovi a punteggio 4')
  await page.getByRole('button', { name: 'Salva', exact: true }).click()

  const presetPill = page.getByRole('button', { name: 'Nuovi a punteggio 4', exact: true })
  await expect(presetPill).toBeVisible()

  // Cambia i filtri: il preset salvato non cambia.
  await page.getByRole('button', { name: '4', exact: true }).click()
  await page.getByRole('button', { name: '5', exact: true }).click()
  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()

  // Riapplicando il preset torna la combinazione salvata (punteggio 4 + nuovo).
  await presetPill.click()
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).not.toBeVisible()

  await page
    .locator('span', { has: presetPill })
    .getByRole('button', { name: 'Elimina filtro salvato' })
    .click()
  await expect(presetPill).not.toBeVisible()
})

test('il filtro ricerca è multi-selezione: più spunte contemporanee e contatore nel trigger', async ({
  page,
  request,
  baseURL,
}) => {
  const { token } = await loginAsSeededUser(page, request, baseURL)

  await request.post(`${baseURL}/api/searches/`, {
    headers: { Authorization: `Token ${token}` },
    data: { keywords: 'Business analyst', city: 'Zurich', country: 'Switzerland' },
  })
  await request.post(`${baseURL}/api/searches/`, {
    headers: { Authorization: `Token ${token}` },
    data: { keywords: 'IT Project manager', city: 'Geneva', country: 'Switzerland' },
  })
  await page.reload()

  const trigger = page.getByRole('button', { name: 'Ricerca', exact: true })
  await expect(trigger).toBeVisible()
  await trigger.click()

  const firstOption = page.getByText('Business analyst — Zurich, Switzerland')
  const secondOption = page.getByText('IT Project manager — Geneva, Switzerland')
  await expect(firstOption).toBeVisible()
  await expect(secondOption).toBeVisible()

  await firstOption.click()
  await expect(page.getByRole('button', { name: 'Ricerca (1)' })).toBeVisible()

  await secondOption.click()
  await expect(page.getByRole('button', { name: 'Ricerca (2)' })).toBeVisible()

  // Rimuovendo una delle due spunte il contatore scende, l'altra resta selezionata.
  await firstOption.click()
  await expect(page.getByRole('button', { name: 'Ricerca (1)' })).toBeVisible()
})

test('il badge candidati evidenzia i job con meno di 25 candidati e mostra il numero esatto quando disponibile', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  await expect(cardFor(page, 'Project Manager').getByText('Tra i primi 25 candidati')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer').getByText('45 candidati')).toBeVisible()
  // Nessun dato candidati per questo job: nessun badge da mostrare.
  await expect(cardFor(page, 'Head of Operations').getByText(/candidat/)).not.toBeVisible()
})

test('l\'icona recruiter è visibile solo per i job con un nome recruiter', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await expect(cardFor(page, 'Backend Developer').getByTitle(/Jane Doe/)).toBeVisible()
  await expect(cardFor(page, 'Project Manager').getByTitle(/Posted by|pubblicato da/i)).not.toBeVisible()
})

test('il filtro candidati mostra solo i job nella fascia selezionata', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await page.getByRole('button', { name: '<25', exact: true }).click()

  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
})

test('il filtro recruiter mostra solo i job con (o senza) un recruiter', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await page.getByLabel('Recruiter').click()
  await page.getByRole('option', { name: 'Con recruiter' }).click()

  await expect(cardFor(page, 'Backend Developer')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
})

test('il cuoricino aggiunge/rimuove un job dalla sezione Preferiti', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  const card = cardFor(page, 'Project Manager')
  await Promise.all([
    page.waitForResponse((response) => response.url().includes('/favorite/') && response.ok()),
    card.getByRole('button', { name: 'Aggiungi ai preferiti' }).click(),
  ])

  await page.getByRole('button', { name: 'Preferiti' }).click()
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()

  await Promise.all([
    page.waitForResponse((response) => response.url().includes('/unfavorite/') && response.ok()),
    cardFor(page, 'Project Manager').getByRole('button', { name: 'Rimuovi dai preferiti' }).click(),
  ])
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
})

test('arricchimento con "salva anche nel profilo" aggiunge il bullet all\'esperienza esistente', async ({
  page,
  request,
  baseURL,
}) => {
  const { token } = await loginAsSeededUser(page, request, baseURL)

  // L'arricchimento (Docs/03 §5.6) si aggancia a un'esperienza già presente
  // nel profilo: non introduce mai un'azienda/ruolo del tutto nuovo, quindi
  // il profilo deve già averne una prima di poterla selezionare nel form.
  const experienceResponse = await request.post(`${baseURL}/api/experiences/`, {
    headers: { Authorization: `Token ${token}` },
    data: { company: 'Beta SpA', role: 'Backend Developer', bullets: ['Bullet iniziale'] },
  })
  const experience = await experienceResponse.json()

  await cardFor(page, 'Backend Developer').getByRole('link', { name: 'Dettagli' }).click()
  await page.waitForURL(/jobs\//)

  await page.getByRole('button', { name: /Aggiungi un'attività/ }).click()
  await page.getByLabel('Esperienza').click()
  await page.getByRole('option', { name: 'Backend Developer — Beta SpA' }).click()
  await page.getByLabel('Nuove attività / competenze').fill('Consulenza backend freelance')
  await page.keyboard.press('Enter')
  await page.getByRole('checkbox', { name: 'Salva anche nel profilo' }).check()

  // Il profilo di questo utente e2e non ha un titolo di studio (nessun
  // onboarding completato, §10.2): la generazione vera e propria viene
  // respinta prima della chiamata a Claude, ma `save_to_profile` è già
  // stato applicato prima di quel controllo (apps/cv/enrichment.py). Il
  // frontend mostra il messaggio esatto restituito dal backend (`detail`),
  // non un testo fisso di "generazione già in corso" (bug corretto).
  await page.getByRole('button', { name: 'Genera CV con questo dettaglio' }).click()
  await expect(
    page.getByText('Completa il profilo (almeno un titolo di studio) prima di generare un CV.'),
  ).toBeVisible({ timeout: 20000 })

  const response = await request.get(`${baseURL}/api/experiences/`, {
    headers: { Authorization: `Token ${token}` },
  })
  const experiences = await response.json()
  const updated = experiences.find((exp) => exp.id === experience.id)
  expect(updated.bullets).toContain('Consulenza backend freelance')
})
