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

// Dettaglio (Sprint 75): azioni nella barra in basso e nel menu ⋯ della testata.
function actionBar(page) {
  return page.getByTestId('action-bar')
}

async function fromMoreMenu(page, item) {
  await page.getByRole('button', { name: 'Altre azioni', exact: true }).click()
  await page.getByRole('menuitem', { name: item }).click()
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

  await page.getByLabel('Cerca per titolo, azienda o località').fill('backend')
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

  // Dallo Sprint 74 si genera solo dal dettaglio (SPEC-DELTA A2); dallo
  // Sprint 75 "Genera CV" della barra apre "Colma i gap" (facoltativo).
  await openCard(page, 'Project Manager')
  await actionBar(page).getByRole('button', { name: 'Genera CV', exact: true }).click()
  const sheet = page.getByRole('dialog', { name: 'Genera CV' })
  await sheet.getByText('1. Nessuna esperienza fintech').click()
  await sheet.getByRole('button', { name: 'Genera CV', exact: true }).click()

  // Durante l'attesa una finestra non chiudibile mostra l'indicatore.
  await expect(page.getByText('Generazione del CV…')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByText('Generazione del CV…')).toBeVisible()

  // Senza ANTHROPIC_API_KEY in questo ambiente la generazione fallisce lato
  // server (gestito, 502): verifichiamo che l'errore sia mostrato e che il
  // job torni allo stato "Nuovo" invece di restare bloccato — il percorso di
  // successo reale richiede una chiave Claude valida (stessa riserva già
  // documentata per import CV e generazione automatica negli sprint precedenti).
  await expect(page.getByText('Non siamo riusciti a generare il CV. Riprova.')).toBeVisible({
    timeout: 20000,
  })
  await expect(page.getByText('Generazione del CV…')).not.toBeVisible()
  await expect(actionBar(page).getByRole('button', { name: 'Genera CV', exact: true })).toBeEnabled()
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
  // essere disponibili. Dallo Sprint 75, senza CV la barra mostra "Genera CV"
  // e "Segna candidatura fatta" è nel menu ⋯.
  await openCard(page, 'Project Manager')
  await page.waitForURL(/jobs\//)
  await expect(page.getByRole('link', { name: "Vai all'annuncio" })).toBeVisible()

  const statusBadge = page.getByTestId('job-status-badge')
  await expect(statusBadge).toHaveText('Nuovo')
  await fromMoreMenu(page, 'Segna candidatura fatta')

  await expect(statusBadge).toHaveText('Candidatura fatta')
  await expect(actionBar(page).getByRole('button', { name: 'Annulla candidatura' })).toBeVisible()
  await page.getByRole('button', { name: 'Altre azioni', exact: true }).click()
  await expect(page.getByRole('menuitem', { name: 'Segna candidatura fatta' })).toHaveCount(0)
})

test('segnare la candidatura come fatta aggiorna lo stato in dettaglio', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await openCard(page, 'Head of Operations')
  await page.waitForURL(/jobs\//)

  // Il seed non crea il PDF del CV: l'azione è nel menu ⋯ (Sprint 75).
  const statusBadge = page.getByTestId('job-status-badge')
  await expect(statusBadge).toHaveText('CV generato', { timeout: 15000 })
  await fromMoreMenu(page, 'Segna candidatura fatta')
  await expect(statusBadge).toHaveText('Candidatura fatta')

  // Annullamento con la finestra di conferma (mockup `undo-application`).
  await actionBar(page).getByRole('button', { name: 'Annulla candidatura' }).click()
  const modal = page.getByRole('dialog', { name: 'Annullare "candidatura fatta"?' })
  await modal.getByRole('button', { name: 'No, lascia com’è' }).click()
  await expect(statusBadge).toHaveText('Candidatura fatta')
  await actionBar(page).getByRole('button', { name: 'Annulla candidatura' }).click()
  await modal.getByRole('button', { name: 'Sì, annulla' }).click()
  // Senza un CV generato il server riporta il job a "Nuovo" (§4.10).
  await expect(statusBadge).toHaveText('Nuovo')
})

test('i contatori corrispondenze/gap rivelano voci e motivazioni', async ({
  page,
  request,
  baseURL,
}) => {
  await loginAsSeededUser(page, request, baseURL)

  await openCard(page, 'Project Manager')
  await page.waitForURL(/jobs\//)

  // Sprint 75: contatori espandibili (mockup `detail-nuovo`), uno aperto per
  // volta; aperti mostrano etichetta e motivo (prima "Espandi motivazioni").
  const matches = page.getByRole('button', { name: '1 corrispondenza' })
  const gaps = page.getByRole('button', { name: '1 gap' })
  await expect(matches).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByText('5+ anni PM')).not.toBeVisible()

  await matches.click()
  await expect(page.getByText('5+ anni PM')).toBeVisible()
  await expect(
    page.getByText("L'offerta richiede almeno 5 anni di esperienza in project management"),
  ).toBeVisible()

  await gaps.click()
  await expect(matches).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByText('5+ anni PM')).not.toBeVisible()
  await expect(page.getByText('Nessuna esperienza fintech')).toBeVisible()
})

test('dettaglio: menu ⋯ da tastiera archivia e riporta dall’archivio', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)
  await openCard(page, 'Project Manager')

  // SPEC-DELTA A7: l'archivio è raggiungibile anche da tastiera (Sprint 75).
  const more = page.getByRole('button', { name: 'Altre azioni', exact: true })
  await more.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('menuitem', { name: 'Archivia' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('menu')).toHaveCount(0)
  await expect(more).toBeFocused()

  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('menuitem', { name: 'Archivia' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Job archiviato.')).toBeVisible()
  await expect(page.getByText('Archiviato', { exact: true })).toBeVisible()

  await more.click()
  await page.getByRole('menuitem', { name: 'Riporta dall’archivio' }).click()
  await expect(page.getByText('Job ripristinato.')).toBeVisible()
  await expect(page.getByText('Archiviato', { exact: true })).toHaveCount(0)
})

test('dettaglio: ▾ di Genera CV apre cover letter e messaggio con il loro costo', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)
  await openCard(page, 'Project Manager')

  const toggle = actionBar(page).getByRole('button', { name: 'Altri documenti da generare' })
  await toggle.click()
  await expect(page.getByRole('menuitem')).toHaveText(['Genera cover letter', 'Genera messaggio'])
  await page.keyboard.press('Escape')
  await expect(toggle).toBeFocused()

  // Il costo mostrato è quello dell'azione del pannello (prima dello Sprint
  // 75 cover letter e messaggio avevano i due testi scambiati).
  await toggle.click()
  await page.getByRole('menuitem', { name: 'Genera cover letter' }).click()
  const coverLetter = page.getByRole('dialog', { name: 'Genera cover letter' })
  await expect(coverLetter.getByTestId('action-cost-cover_letter')).toBeVisible()
  await expect(coverLetter.getByTestId('action-cost-referral_message')).toHaveCount(0)
  await expect(coverLetter.getByLabel('Indicazioni per questa cover letter (facoltativo)')).toHaveAttribute('maxlength', '2000')
  await coverLetter.getByRole('button', { name: 'Annulla' }).click()

  await toggle.click()
  await page.getByRole('menuitem', { name: 'Genera messaggio' }).click()
  const message = page.getByRole('dialog', { name: 'Genera messaggio di networking' })
  await expect(message.getByTestId('action-cost-referral_message')).toBeVisible()
  await expect(message.getByTestId('action-cost-cover_letter')).toHaveCount(0)
  await expect(message.getByRole('radio', { name: 'LinkedIn' })).toBeChecked()
  await message.getByRole('button', { name: 'Annulla' }).click()
  await expect(message).not.toBeVisible()
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

  // Sprint 75: nel dettaglio la barra azione sostituisce la barra di tab.
  test('nel dettaglio la barra azione sostituisce la barra di tab', async ({ page, request, baseURL }) => {
    await loginAsSeededUser(page, request, baseURL)
    await openCard(page, 'Project Manager')
    await expect(page.getByRole('navigation', { name: 'Navigazione principale' })).not.toBeVisible()
    const bar = actionBar(page)
    await expect(bar.getByRole('button', { name: 'Genera CV', exact: true })).toBeVisible()
    const box = await bar.boundingBox()
    expect(box.y + box.height).toBeGreaterThan(840)
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)

    await page.getByRole('link', { name: 'Jobs', exact: true }).click()
    await expect(page).toHaveURL(/\/list/)
    await expect(page.getByRole('navigation', { name: 'Navigazione principale' })).toBeVisible()
  })
})

// --- Sprint 82 (SPEC-DELTA A16): contratto e stipendio. Nel seed: Project
// Manager full-time con stipendio, Backend Developer part-time, Head of
// Operations full-time senza stipendio, Data Analyst temporaneo con
// stipendio; Consulente HR (importato) senza dati.

test('filtri Contratto (multi) e Stipendio, anche combinati e nei filtri salvati', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'Part-time', exact: true }).click())
  await expect(cardFor(page, 'Backend Developer')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
  await expect(page).toHaveURL(/contract=part_time/)

  // OR dentro il gruppo: Part-time + Full-time.
  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'Full-time', exact: true }).click())
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Data Analyst')).not.toBeVisible()

  // AND con Stipendio: resta solo il Project Manager.
  await inFilters(page, (sheet) => sheet.getByText('Con stipendio', { exact: true }).click())
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Head of Operations')).not.toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()
  await expect(page.getByRole('button', { name: /^Filtri \(2\)/ })).toBeVisible()

  // Il filtro salvato conserva Contratto e Stipendio.
  await page.getByRole('button', { name: /^Filtri/ }).click()
  await page.getByRole('dialog', { name: 'Filtri' }).getByRole('button', { name: 'Salva filtri attuali' }).click()
  const saveDialog = page.getByRole('dialog', { name: 'Salva filtri attuali' })
  await saveDialog.getByLabel('Nome').fill('Pagati full o part')
  await saveDialog.getByRole('button', { name: 'Salva', exact: true }).click()
  await expect(saveDialog).not.toBeVisible()
  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'Azzera filtri' }).click())
  await expect(cardFor(page, 'Data Analyst')).toBeVisible()
  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'Pagati full o part', exact: true }).click())
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Data Analyst')).not.toBeVisible()
  await expect(page).toHaveURL(/salary=yes/)

  // Senza stipendio: i job senza il dato.
  await inFilters(page, async (sheet) => {
    await sheet.getByRole('button', { name: 'Azzera filtri' }).click()
    await sheet.getByText('Senza stipendio', { exact: true }).click()
  })
  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
})

test('dettaglio: stipendio e contratto solo quando presenti', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await openCard(page, 'Project Manager')
  const row = page.getByTestId('job-pay-contract')
  await expect(row.getByText('€45.000 – €55.000')).toBeVisible()
  await expect(row.getByText('Full-time')).toBeVisible()

  await page.goBack()
  await openCard(page, 'Head of Operations')
  await expect(page.getByTestId('job-pay-contract').getByText('Full-time')).toBeVisible()
  await expect(page.getByTestId('job-pay-contract')).not.toContainText('€')

  // Job importato senza stipendio né contratto: nessuna riga.
  await page.goto('/list?section=imported')
  await openCard(page, 'Consulente HR')
  await expect(page.getByRole('heading', { name: 'Consulente HR', level: 1 })).toBeVisible()
  await expect(page.getByTestId('job-pay-contract')).toHaveCount(0)
})

// --- Sprint 84 (SPEC-DELTA A18–A19): modalità di lavoro dallo scoring ed
// etichetta Desiderio. Nel seed: Project Manager ibrido e "Desiderio",
// Backend Developer remoto, Head of Operations "Non indicata", gli altri
// senza modalità (job di prima dello sprint).

test('filtro Modalità e chip "Lavoro dei desideri"; etichette su card e dettaglio', async ({ page, request, baseURL }) => {
  await loginAsSeededUser(page, request, baseURL)

  await expect(cardFor(page, 'Project Manager').getByTestId('job-wish-badge')).toHaveText('Desiderio')
  await expect(cardFor(page, 'Backend Developer').getByTestId('job-wish-badge')).toHaveCount(0)

  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'Remoto', exact: true }).click())
  await expect(page).toHaveURL(/mode=remote/)
  await expect(cardFor(page, 'Backend Developer')).toBeVisible()
  await expect(cardFor(page, 'Project Manager')).not.toBeVisible()
  // OR nel gruppo; i job senza modalità (raccolti prima) restano fuori.
  await inFilters(page, (sheet) => sheet.getByRole('button', { name: 'Non indicata', exact: true }).click())
  await expect(cardFor(page, 'Head of Operations')).toBeVisible()
  await expect(cardFor(page, 'Data Analyst')).not.toBeVisible()
  await expect(page.getByRole('button', { name: /^Filtri \(1\)/ })).toBeVisible()

  // "Lavoro dei desideri" è il primo chip del gruppo Ricerca.
  await inFilters(page, async (sheet) => {
    await sheet.getByRole('button', { name: 'Azzera filtri' }).click()
    const searchGroup = sheet.getByRole('group', { name: 'Ricerca di provenienza' })
    await expect(searchGroup.getByRole('button').first()).toHaveText('Lavoro dei desideri')
    await sheet.getByRole('button', { name: 'Lavoro dei desideri', exact: true }).click()
  })
  await expect(page).toHaveURL(/search=wish/)
  await expect(cardFor(page, 'Project Manager')).toBeVisible()
  await expect(cardFor(page, 'Backend Developer')).not.toBeVisible()

  await openCard(page, 'Project Manager')
  await expect(page.getByTestId('job-wish-badge')).toHaveText('Lavoro dei desideri')
  await expect(page.getByTestId('job-work-mode')).toContainText('Ibrido')
  await page.goBack()
  await page.goto('/list')
  await openCard(page, 'Head of Operations')
  await expect(page.getByRole('heading', { name: 'Head of Operations', level: 1 })).toBeVisible()
  await expect(page.getByTestId('job-work-mode')).toHaveCount(0)
})
