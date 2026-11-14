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

// Codice di invito del backend di prova (Sprint 66), vuoto se la registrazione è aperta.
const INVITE_CODE = process.env.E2E_INVITE_CODE || ''

let uniqueSuffix = 0
async function registerUser(request, baseURL) {
  uniqueSuffix += 1
  const email = `e2e-jobs-${Date.now()}-${uniqueSuffix}@example.com`
  const password = 'SuperSecret123!'
  const response = await request.post(`${baseURL}/api/accounts/register/`, {
    data: { email, password, invite_code: INVITE_CODE, accept_privacy: true, accept_terms: true, confirm_age: true },
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

// Dallo Sprint 74 i filtri sono nel pannello "Filtri" (prima in pagina; il
// punteggio era una tendina dallo Sprint 47): si apre il pannello, si agisce
// sui controlli e lo si chiude con "Mostra risultati". I filtri si applicano
// subito e restano nella query string, come prima.
async function inFilters(page, action) {
  await page.getByRole('button', { name: /^Filtri/ }).click()
  const sheet = page.getByRole('dialog', { name: 'Filtri' })
  await expect(sheet).toBeVisible()
  await action(sheet)
  await sheet.getByRole('button', { name: 'Mostra risultati' }).click()
  await expect(sheet).not.toBeVisible()
}

async function toggleScore(page, value) {
  await inFilters(page, (sheet) => sheet.getByRole('button', { name: value, exact: true }).click())
}

// Dallo Sprint 74 la card è tutta cliccabile (link sul titolo) e non ha più
// i pulsanti "Dettagli" / "Archivia" / "Genera CV".
async function openCard(page, title) {
  await cardFor(page, title).getByRole('link', { name: title }).click()
  await page.waitForURL(/jobs\//)
}

async function swipeCard(page, title) {
  const card = cardFor(page, title)
  // La card può essere sotto la piega del viewport (720 px): il mouse fuori
  // schermo non genera eventi.
  await card.scrollIntoViewIfNeeded()
  const box = await card.boundingBox()
  await page.mouse.move(box.x + box.width - 20, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x - 120, box.y + box.height / 2, { steps: 10 })
  await page.mouse.up()
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
  await toggleScore(page, '4')

  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).not.toBeVisible()
})

test('filtro stato mostra solo i job nello stato selezionato', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'CV generato' }).click())

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
  await toggleScore(page, '5')
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()

  await page.getByPlaceholder('Cerca titolo, azienda, località').fill('backend')
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
  await swipeCard(page, 'Backend Developer')

  await expect(card).not.toBeVisible()
  const undoButton = page.getByRole('status').getByRole('button', { name: 'Annulla' })
  await expect(undoButton).toBeVisible()
  await undoButton.click()

  await expect(cardFor(page, 'Backend Developer')).toBeVisible()
})

test('swipe reale (drag) archivia un job', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await swipeCard(page, 'Project Manager')

  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
  await expect(page.getByText('Job archiviato.')).toBeVisible()
})

test('generare il CV disabilita il pulsante e mostra il caricamento', async ({ page, request, baseURL }) => {
  const { token } = await loginAsSeededUser(page, request, baseURL)
  // Dagli Sprint 26/70 la generazione richiede un profilo completo (almeno un
  // titolo di studio): senza, il server risponde subito 409 e il caricamento
  // non si vede. Si aggiunge un titolo di studio via API.
  const education = await request.post(`${baseURL}/api/educations/`, {
    headers: { Authorization: `Token ${token}` },
    data: { institution: 'Politecnico di Milano', title: 'Laurea in Informatica', end_date: '2020-07-01' },
  })
  expect(education.ok()).toBe(true)

  // Dallo Sprint 74 si genera solo dal dettaglio (SPEC-DELTA A2).
  await openCard(page, 'Project Manager')
  await page.getByRole('button', { name: 'Genera CV', exact: true }).click()

  // Durante l'attesa il pulsante è disabilitato e mostra l'indicatore.
  await expect(page.getByRole('button', { name: 'Generazione…' }).first()).toBeDisabled()

  // Senza ANTHROPIC_API_KEY in questo ambiente la generazione fallisce lato
  // server (gestito, 502): verifichiamo che l'errore sia mostrato e che il
  // job torni allo stato "Nuovo" invece di restare bloccato — il percorso di
  // successo reale richiede una chiave Claude valida (stessa riserva già
  // documentata per import CV e generazione automatica negli sprint precedenti).
  await expect(page.getByText('Non siamo riusciti a generare il CV. Riprova.')).toBeVisible({
    timeout: 20000,
  })
  await expect(page.getByRole('button', { name: 'Genera CV', exact: true })).toBeEnabled()
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
  await openCard(page, 'Project Manager')
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

  await openCard(page, 'Head of Operations')
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

  await openCard(page, 'Project Manager')
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

  await inFilters(page, async (sheet) => {
    await sheet.getByPlaceholder('Filtra per città o paese…').fill('Torino')
    await page.waitForTimeout(400)
  })

  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
})

test('salvare, applicare e rimuovere un filtro preferito', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  // Imposta punteggio 4 e stato "Nuovo": isola "Project Manager" (score 4,
  // nuovo) escludendo "Head of Operations" (score 5, CV generato).
  await inFilters(page, async (sheet) => {
    await sheet.getByRole('button', { name: '4', exact: true }).click()
    await sheet.getByRole('button', { name: 'Nuovo', exact: true }).click()
  })
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).not.toBeVisible()

  // "Salva filtri attuali" è nel pannello e apre una finestra con il nome.
  await page.getByRole('button', { name: /^Filtri/ }).click()
  await page.getByRole('dialog', { name: 'Filtri' }).getByRole('button', { name: 'Salva filtri attuali' }).click()
  const saveDialog = page.getByRole('dialog', { name: 'Salva filtri attuali' })
  await saveDialog.getByLabel('Nome').fill('Nuovi a punteggio 4')
  await saveDialog.getByRole('button', { name: 'Salva', exact: true }).click()
  await expect(saveDialog).not.toBeVisible()

  // Cambia i filtri: il preset salvato non cambia. Si toglie anche "Nuovo":
  // "Head of Operations" (score 5) è "CV generato" nei dati di prova.
  await inFilters(page, async (sheet) => {
    await expect(sheet.getByRole('button', { name: 'Nuovi a punteggio 4', exact: true })).toBeVisible()
    await sheet.getByRole('button', { name: '4', exact: true }).click()
    await sheet.getByRole('button', { name: '5', exact: true }).click()
    await sheet.getByRole('button', { name: 'Nuovo', exact: true }).click()
  })
  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()

  // Riapplicando il preset torna la combinazione salvata (punteggio 4 + nuovo).
  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'Nuovi a punteggio 4', exact: true }).click())
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).not.toBeVisible()

  await inFilters(page, async (sheet) => {
    await sheet.getByRole('button', { name: 'Elimina filtro salvato: Nuovi a punteggio 4' }).click()
    await expect(sheet.getByRole('button', { name: 'Nuovi a punteggio 4', exact: true })).not.toBeVisible()
  })
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

  // Dallo Sprint 74 le ricerche di provenienza sono pillole nel pannello
  // "Filtri" (prima una tendina "Ricerca (N)"): si combinano in OR.
  await page.getByRole('button', { name: /^Filtri/ }).click()
  const sheet = page.getByRole('dialog', { name: 'Filtri' })
  const firstOption = sheet.getByRole('button', { name: 'Business analyst · Zurich' })
  const secondOption = sheet.getByRole('button', { name: 'IT Project manager · Geneva' })
  await expect(firstOption).toHaveAttribute('aria-pressed', 'false')
  await expect(secondOption).toHaveAttribute('aria-pressed', 'false')

  await firstOption.click()
  await expect(firstOption).toHaveAttribute('aria-pressed', 'true')
  await expect(page).toHaveURL(/search=\d+/)

  await secondOption.click()
  await expect(firstOption).toHaveAttribute('aria-pressed', 'true')
  await expect(secondOption).toHaveAttribute('aria-pressed', 'true')
  await expect(page).toHaveURL(/search=\d+%2C\d+|search=\d+,\d+/)

  // Rimuovendo una delle due selezioni l'altra resta selezionata.
  await firstOption.click()
  await expect(firstOption).toHaveAttribute('aria-pressed', 'false')
  await expect(secondOption).toHaveAttribute('aria-pressed', 'true')
  await sheet.getByRole('button', { name: 'Mostra risultati' }).click()
  await expect(page.getByRole('button', { name: 'Filtri (1)' })).toBeVisible()
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

  await inFilters(page, (sheet) => sheet.getByRole('button', { name: '<25', exact: true }).click())

  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
})

test('il filtro recruiter mostra solo i job con (o senza) un recruiter', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  // Segmento Tutti / Con recruiter / Senza recruiter: radio nascosti, si clicca l'etichetta.
  await inFilters(page, (sheet) => sheet.getByText('Con recruiter', { exact: true }).click())

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

  // "Preferiti" è anche nel nome dei cuoricini ("Aggiungi ai preferiti", Sprint 46).
  await page.getByRole('button', { name: 'Preferiti', exact: true }).click()
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()

  await Promise.all([
    page.waitForResponse((response) => response.url().includes('/unfavorite/') && response.ok()),
    cardFor(page, 'Project Manager').getByRole('button', { name: 'Rimuovi dai preferiti' }).click(),
  ])
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
})

// Sprint 68: sezione e filtri nella query string.
test('i filtri restano nell\'URL: tornando dal dettaglio la lista è ancora filtrata', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  await toggleScore(page, '4')
  await expect(page).toHaveURL(/score=4/)
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()

  await openCard(page, 'Project Manager')
  await page.waitForURL(/jobs\//)
  await page.goBack()

  await expect(page).toHaveURL(/score=4/)
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
})

// Sprint 73 (SPEC-DELTA A9): "Esci" non è più nella barra in alto ma in
// fondo alle Impostazioni, con finestra di conferma.
test('Esci da Impostazioni chiede conferma e chiude la sessione', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)
  await expect(page.getByRole('button', { name: 'Esci' })).toHaveCount(0)

  await page.getByRole('navigation', { name: 'Navigazione principale' }).getByRole('link', { name: 'Impostazioni' }).click()
  await page.waitForURL(/\/settings$/)
  await page.getByRole('button', { name: 'Esci' }).click()

  const dialog = page.getByRole('dialog', { name: 'Vuoi uscire?' })
  await expect(dialog).toBeVisible()
  // "Annulla" chiude la finestra senza uscire.
  await dialog.getByRole('button', { name: 'Annulla' }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page).toHaveURL(/\/settings$/)

  await page.getByRole('button', { name: 'Esci' }).click()
  await page.getByRole('dialog', { name: 'Vuoi uscire?' }).getByRole('button', { name: 'Esci' }).click()
  await expect(page).toHaveURL(/\/login$/)
  await page.goto('/list')
  await expect(page).toHaveURL(/\/login$/)
})

// Sprint 73: navigazione a 3 voci (SPEC-DELTA A1). Da 1024 px barra in alto;
// la Home non esiste più e /home porta alla lista.
test('navigazione a 3 voci in alto su desktop e /home reindirizza a /list', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)
  const nav = page.getByRole('navigation', { name: 'Navigazione principale' })
  await expect(nav.getByRole('link')).toHaveText(['Jobs', 'Profilo', 'Impostazioni'])
  await expect(nav.getByRole('link', { name: 'Jobs' })).toHaveAttribute('aria-current', 'page')

  // Jobs resta la voce attiva anche nel dettaglio di un job.
  await openCard(page, 'Project Manager')
  await page.waitForURL(/jobs\//)
  await expect(nav.getByRole('link', { name: 'Jobs' })).toHaveAttribute('aria-current', 'page')

  await nav.getByRole('link', { name: 'Profilo' }).click()
  await expect(page).toHaveURL(/\/profile$/)
  await expect(nav.getByRole('link', { name: 'Profilo' })).toHaveAttribute('aria-current', 'page')

  await page.goto('/home')
  await expect(page).toHaveURL(/\/list$/)
})

test.describe('navigazione su mobile', () => {
  test.use({ viewport: { width: 390, height: 844 } })
  test('barra di tab in basso con 3 voci e Raccogli raggiungibile dalla lista', async ({ page, request, baseURL }) => {
    await loginAsSeededUser(page, request, baseURL)
    const tabs = page.getByRole('navigation', { name: 'Navigazione principale' })
    await expect(tabs).toHaveCount(1)
    await expect(tabs.getByRole('link')).toHaveText(['Jobs', 'Profilo', 'Impostazioni'])
    const box = await tabs.boundingBox()
    expect(box.y + box.height).toBeGreaterThan(830)

    // La raccolta manuale (prima nella Home) si apre dal pulsante accanto al titolo.
    await page.getByRole('button', { name: 'Raccogli nuovi job' }).click()
    const sheet = page.getByRole('dialog', { name: 'Raccogli nuovi job' })
    await expect(sheet.getByRole('button', { name: 'Raccogli ora' })).toBeVisible()
    await sheet.getByRole('button', { name: 'Chiudi' }).click()
    await expect(sheet).not.toBeVisible()

    // Nessuna pagina più larga dello schermo.
    for (const path of ['/list', '/profile', '/settings']) {
      await page.goto(path)
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    }
  })
})
