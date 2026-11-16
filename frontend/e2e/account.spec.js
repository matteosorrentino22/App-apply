import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_DIR = path.resolve(__dirname, '../../backend')
const BACKEND_ENV = {
  ...process.env,
  DJANGO_SECRET_KEY: 'dev-insecure-secret-key',
  DJANGO_DEBUG: 'true',
  DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
  POSTGRES_HOST: 'localhost',
}

function setAccount(email, { plan = 'pro', credit = '7.50' } = {}) {
  execFileSync(
    '.venv/bin/python',
    ['manage.py', 'set_e2e_account', email, `--plan=${plan}`, `--credit=${credit}`],
    { cwd: BACKEND_DIR, env: BACKEND_ENV },
  )
}

// Codice di invito del backend di prova (Sprint 66), vuoto se la registrazione è aperta.
const INVITE_CODE = process.env.E2E_INVITE_CODE || ''

let uniqueSuffix = 0
async function registerUser(request, baseURL) {
  uniqueSuffix += 1
  const email = `e2e-acc-${Date.now()}-${uniqueSuffix}@example.com`
  const password = 'SuperSecret123!'
  const response = await request.post(`${baseURL}/api/accounts/register/`, {
    data: { email, password, invite_code: INVITE_CODE, accept_privacy: true, accept_terms: true, confirm_age: true },
  })
  const body = await response.json()
  return { email, password, token: body.token }
}

async function login(page, email, password) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()
  await page.waitForURL(/onboarding|list/)
  await page.goto('/settings')
}

test('la schermata account mostra piano e saldo credito impostati da amministratore', async ({
  page,
  request,
  baseURL,
}) => {
  const { email, password } = await registerUser(request, baseURL)
  setAccount(email, { plan: 'pro', credit: '42.00' })

  await login(page, email, password)

  await expect(page.getByText('Pro', { exact: true })).toBeVisible()
  await expect(page.getByText('42,00 €')).toBeVisible()
})

// Sprint 78: le ricerche sono nella sottopagina /settings/searches; la nuova
// ricerca si crea in un pannello, attivazione con l'interruttore della card,
// eliminazione con conferma.
async function addSearchFromSheet(page, keywords, city, country) {
  await page.getByRole('button', { name: 'Nuova ricerca' }).click()
  const sheet = page.getByRole('dialog', { name: 'Nuova ricerca' })
  await expect(sheet.getByText('La nuova ricerca nasce disattivata')).toBeVisible()
  await sheet.getByLabel('Parole chiave').fill(keywords)
  await sheet.getByLabel('Città', { exact: true }).fill(city)
  await sheet.getByLabel('Paese', { exact: true }).fill(country)
  await sheet.getByRole('button', { name: 'Aggiungi ricerca' }).click()
  return sheet
}

test('crea, attiva, disattiva ed elimina una ricerca salvata', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)
  await page.getByRole('link', { name: /Ricerche salvate/ }).click()
  await expect(page).toHaveURL(/\/settings\/searches$/)

  const sheet = await addSearchFromSheet(page, 'project manager', 'Milano', 'Italia')
  await expect(sheet).not.toBeVisible()
  const card = page.getByTestId('search-card')
  await expect(card.getByText('project manager', { exact: true })).toBeVisible()
  await expect(card.getByText('Milano, Italia')).toBeVisible()
  await expect(card.getByText('Disattivata')).toBeVisible()

  const toggle = card.getByRole('switch', { name: 'Usa la ricerca «project manager»' })
  await toggle.click()
  await expect(card.getByText('In uso')).toBeVisible()
  await toggle.click()
  await expect(card.getByText('Disattivata')).toBeVisible()

  await card.getByRole('button', { name: 'Elimina', exact: true }).click()
  const modal = page.getByRole('dialog', { name: 'Eliminare la ricerca?' })
  await modal.getByRole('button', { name: 'Annulla' }).click()
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: 'Elimina', exact: true }).click()
  await modal.getByRole('button', { name: 'Elimina', exact: true }).click()
  await expect(page.getByText('Milano, Italia')).not.toBeVisible()
  await expect(page.getByText('Nessuna ricerca salvata.')).toBeVisible()

  // Indietro del browser: si torna all'elenco delle Impostazioni.
  await page.goBack()
  await expect(page).toHaveURL(/\/settings$/)
  await expect(page.getByRole('heading', { name: 'Impostazioni', level: 1 })).toBeVisible()
})

test('mostra il messaggio del limite di piano oltre le ricerche salvate consentite', async ({
  page,
  request,
  baseURL,
}) => {
  const { email, password, token } = await registerUser(request, baseURL)

  // Piano Free di default: 10 ricerche salvate massime (services.PLAN_LIMITS).
  for (let i = 0; i < 10; i += 1) {
    await request.post(`${baseURL}/api/searches/`, {
      headers: { Authorization: `Token ${token}` },
      data: { keywords: `developer ${i}`, city: 'Roma', country: 'Italia' },
    })
  }

  await login(page, email, password)
  await page.goto('/settings/searches')

  const sheet = await addSearchFromSheet(page, 'developer', 'Roma', 'Italia')
  await expect(
    sheet.getByText('Hai raggiunto il numero massimo di ricerche salvate per il tuo piano.'),
  ).toBeVisible()
})

test('le impostazioni persistono dopo il reload della pagina', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)

  // Sprint 78: la lingua del CV in un pannello, la foto con un interruttore.
  await page.getByTestId('settings-cv-language').click()
  await page.getByRole('dialog', { name: 'Lingua del CV generato' }).getByText('Sempre in inglese').click()
  await expect(page.getByText('Impostazioni salvate.').first()).toBeVisible()
  await expect(page.getByTestId('settings-cv-language')).toContainText('Sempre in inglese')
  const photo = page.getByRole('switch', { name: 'Includi la foto nel CV' })
  await photo.click()
  await expect(photo).toHaveAttribute('aria-checked', 'true')

  await page.reload()

  await expect(page.getByTestId('settings-cv-language')).toContainText('Sempre in inglese')
  await page.getByTestId('settings-cv-language').click()
  await expect(page.getByRole('dialog', { name: 'Lingua del CV generato' }).getByRole('radio', { name: 'Sempre in inglese' })).toBeChecked()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('switch', { name: 'Includi la foto nel CV' })).toHaveAttribute('aria-checked', 'true')
})

test('su iOS senza installazione alla home mostra l\'istruzione dedicata', async ({
  request,
  baseURL,
  browser,
}) => {
  const iosContext = await browser.newContext({
    baseURL,
    locale: 'it-IT',
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  })
  const iosPage = await iosContext.newPage()
  const { email, password } = await registerUser(request, baseURL)
  await login(iosPage, email, password)

  await expect(iosPage.getByText(/aggiungi questa app alla schermata Home/)).toBeVisible()
  await expect(iosPage.getByRole('button', { name: 'Attiva notifiche' })).not.toBeVisible()

  await iosContext.close()
})

// Sprint 70: titolo della pagina e "I tuoi limiti di oggi".
test('Impostazioni: titolo corretto e limiti di oggi con massimali e prezzi', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)

  await expect(page.getByRole('heading', { name: 'Impostazioni', level: 1 })).toBeVisible()
  // Sprint 78: sottopagina /settings/limits.
  await page.getByRole('link', { name: /I tuoi limiti di oggi/ }).click()
  await expect(page.getByRole('heading', { name: 'I tuoi limiti di oggi', level: 1 })).toBeVisible()
  // Utente Free appena registrato: 0 generazioni CV su 1, 1,50 € oltre il massimale.
  const cvRow = page.getByTestId('usage-row-cv')
  await expect(cvRow).toContainText('0 / 1')
  await expect(cvRow).toContainText('1,50')
  await expect(page.getByTestId('usage-row-import')).toContainText('Solo piano Pro')
  // Sprint 77: una sola riga per la raccolta del giorno (automatica o manuale).
  const collectionRow = page.getByTestId('usage-row-collection')
  await expect(collectionRow).toContainText('Raccolta giornaliera')
  await expect(collectionRow).toContainText('0 / 1')
})

// Sprint 78: privacy e sicurezza in una sottopagina con link diretto; cambio
// password in un pannello, eliminazione dell'account in una finestra.
test('privacy e sicurezza: link diretto, password, documenti, eliminazione account', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)
  await page.goto('/settings/privacy')
  await expect(page.getByRole('heading', { name: 'Privacy e sicurezza', level: 1 })).toBeVisible()
  await expect(page.getByRole('main').getByRole('link', { name: /Informativa privacy/ })).toContainText('accettata il')
  await expect(page.getByText('Età minima')).toBeVisible()

  await page.getByTestId('settings-password').click()
  const sheet = page.getByRole('dialog', { name: 'Cambia password' })
  await sheet.getByLabel('Password attuale').fill(password)
  await sheet.getByLabel('Nuova password', { exact: true }).fill('NuovaPassword123!')
  await sheet.getByLabel('Ripeti la nuova password').fill('Diversa123!')
  await sheet.getByRole('button', { name: 'Cambia password' }).click()
  await expect(sheet.getByText('Le due password non coincidono.')).toBeVisible()
  await page.keyboard.press('Escape')

  await page.getByRole('button', { name: 'Elimina account' }).click()
  const modal = page.getByRole('dialog', { name: 'Eliminare definitivamente l’account?' })
  const submit = modal.getByRole('button', { name: 'Elimina definitivamente' })
  await expect(submit).toBeDisabled()
  await modal.getByLabel('Password').fill(password)
  await expect(submit).toBeDisabled()
  await modal.getByText('Ho capito che tutti i miei dati').click()
  await expect(submit).toBeEnabled()
  await modal.getByRole('button', { name: 'Annulla' }).click()
  await expect(modal).not.toBeVisible()

  await page.getByRole('link', { name: 'Impostazioni' }).first().click()
  await expect(page).toHaveURL(/\/settings$/)
})

test('raccolta automatica nell’elenco: bloccata per i Free, attivabile dai Pro con l’orario', async ({ page, request, baseURL }) => {
  const free = await registerUser(request, baseURL)
  await login(page, free.email, free.password)
  const row = page.getByTestId('settings-auto-collection')
  await expect(row).toContainText('Solo piano Pro')
  await expect(row.getByRole('switch', { name: 'Raccolta automatica' })).toBeDisabled()

  const pro = await registerUser(request, baseURL)
  setAccount(pro.email, { plan: 'pro', credit: '0' })
  await login(page, pro.email, pro.password)
  const proRow = page.getByTestId('settings-auto-collection')
  await proRow.getByRole('switch', { name: 'Raccolta automatica' }).click()
  await expect(proRow).toContainText('Ogni giorno alle 07:00')
  await expect(proRow.getByRole('combobox', { name: 'Orario di avvio' })).toHaveText('07:00')
})

test('profilo: sezioni a fisarmonica e "Salva modifiche" nella barra in basso', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)
  await page.goto('/profile')
  await expect(page.getByRole('heading', { name: 'Profilo', level: 1 })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Dati di contatto' })).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByRole('button', { name: /^Esperienze/ })).toHaveAttribute('aria-expanded', 'false')

  await page.getByLabel('Nome', { exact: true }).fill('Mario')
  await page.getByLabel('Cognome').fill('Rossi')
  await page.getByLabel('Telefono').fill('+39 000 0000000')
  await page.getByLabel('Città', { exact: true }).fill('Milano')
  await page.getByLabel('Paese', { exact: true }).fill('Italia')
  // Contatti chiusi con un campo obbligatorio vuoto: salvando la sezione si riapre.
  await page.getByLabel('Nome', { exact: true }).fill('')
  await page.getByRole('button', { name: 'Dati di contatto' }).click()
  await page.getByRole('button', { name: 'Salva modifiche' }).click()
  await expect(page.getByRole('button', { name: 'Dati di contatto' })).toHaveAttribute('aria-expanded', 'true')
  await page.getByLabel('Nome', { exact: true }).fill('Mario')

  await page.getByRole('button', { name: 'Salva modifiche' }).click()
  await expect(page.getByText('Profilo aggiornato.').first()).toBeVisible()
  await expect(page.getByText('Mario Rossi')).toBeVisible()
})

// Sprint 81 (prova su iPhone): nelle sezioni principali la barra di tab resta
// visibile; "Salva modifiche" compare sopra di essa solo con modifiche non
// salvate; "Nuova ricerca" sta sopra la barra di tab. Date: "In corso"
// disattiva e svuota la data di fine.
test.describe('barre in basso su mobile', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('Profilo e Ricerche: barra di tab sempre visibile, barra azione sopra', async ({ page, request, baseURL }) => {
    const { email, password } = await registerUser(request, baseURL)
    await login(page, email, password)
    const tabbar = page.getByRole('navigation', { name: 'Navigazione principale' })
    const bar = page.getByTestId('action-bar')

    await page.goto('/profile')
    await expect(page.getByRole('heading', { name: 'Profilo', level: 1 })).toBeVisible()
    await expect(tabbar).toBeVisible()
    await expect(bar).toHaveCount(0)

    await page.getByLabel('Telefono').fill('+39 000 0000000')
    await expect(bar.getByRole('button', { name: 'Salva modifiche' })).toBeVisible()
    await expect(tabbar).toBeVisible()
    const barBox = await bar.boundingBox()
    const tabBox = await tabbar.boundingBox()
    expect(barBox.y + barBox.height).toBeLessThanOrEqual(tabBox.y + 1)
    // Il contenuto ha lo spazio in fondo per entrambe le barre.
    const pad = await page.evaluate(() => parseFloat(getComputedStyle(document.querySelector('#root > div')).paddingBottom))
    expect(pad).toBeGreaterThanOrEqual(barBox.height + tabBox.height - 1)
    // Tornare al valore di partenza = nessuna modifica: la barra sparisce.
    await page.getByLabel('Telefono').fill('')
    await expect(bar).toHaveCount(0)

    // Esperienza: "In corso" disattiva e svuota la data di fine.
    await page.getByRole('button', { name: /^Esperienze/ }).click()
    await page.getByRole('button', { name: 'Aggiungi azienda' }).click()
    await page.getByLabel('Data fine').fill('2024-06-30')
    await expect(page.getByLabel('Data fine')).toHaveValue('2024-06-30')
    await page.getByRole('checkbox', { name: 'In corso' }).click()
    await expect(page.getByLabel('Data fine')).toBeDisabled()
    await expect(page.getByLabel('Data fine')).toHaveValue('')
    await expect(bar.getByRole('button', { name: 'Salva modifiche' })).toBeVisible()

    // Dalla barra di tab si cambia sezione anche con modifiche in corso.
    await tabbar.getByRole('link', { name: 'Impostazioni' }).click()
    await expect(page).toHaveURL(/\/settings$/)

    await page.goto('/settings/searches')
    await expect(tabbar).toBeVisible()
    await expect(bar.getByRole('button', { name: 'Nuova ricerca' })).toBeVisible()
    const searchBar = await bar.boundingBox()
    const searchTab = await tabbar.boundingBox()
    expect(searchBar.y + searchBar.height).toBeLessThanOrEqual(searchTab.y + 1)
  })
})

// Sprint 82 (SPEC-DELTA A15): attività del Profilo come chip modificabili.
test('profilo: attività come chip, modifica con contatore, limiti di 400 caratteri e 15 attività', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)
  await page.goto('/profile')
  await page.getByRole('button', { name: /^Esperienze/ }).click()
  await page.getByRole('button', { name: 'Aggiungi azienda' }).click()
  await expect(page.getByText('Nessuna attività inserita.')).toBeVisible()

  const input = page.getByLabel('Attività / competenze in questo ruolo')
  await input.fill('Reporting mensile')
  await input.press('Enter')
  const chips = page.getByTestId('activity-chip')
  await expect(chips).toHaveCount(1)
  await expect(page.getByText('Tocca un’attività per modificarla.', { exact: false })).toBeVisible()

  // Tocco sul testo → modifica con contatore; oltre 400 caratteri "Fatto" è disattivato.
  await page.getByRole('button', { name: 'Modifica l’attività: Reporting mensile' }).click()
  const editor = page.getByLabel('Testo dell’attività')
  await expect(page.getByText('17 / 400')).toBeVisible()
  await editor.fill('x'.repeat(401))
  await expect(page.getByText('401 / 400')).toBeVisible()
  await expect(page.getByRole('alert').filter({ hasText: 'supera i 400 caratteri' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Fatto' })).toBeDisabled()
  await editor.fill('Reporting mensile alla direzione')
  await page.getByRole('button', { name: 'Fatto' }).click()
  await expect(chips).toHaveText(['Reporting mensile alla direzione'])

  // Annulla non cambia nulla.
  await page.getByRole('button', { name: /^Modifica l’attività/ }).click()
  await page.getByLabel('Testo dell’attività').fill('Da scartare')
  await page.getByRole('button', { name: 'Annulla' }).click()
  await expect(chips).toHaveText(['Reporting mensile alla direzione'])

  // ✕ elimina.
  await page.getByRole('button', { name: 'Rimuovi Reporting mensile alla direzione' }).click()
  await expect(chips).toHaveCount(0)

  // A 15 attività il campo si blocca con il messaggio.
  for (let i = 1; i <= 15; i++) {
    await input.fill(`Attività numero ${i}`)
    await input.press('Enter')
  }
  await expect(chips).toHaveCount(15)
  await expect(input).toBeDisabled()
  await expect(input).toHaveAttribute('placeholder', 'Hai raggiunto il massimo di 15 attività')
  await expect(page.getByText('Elimina un’attività per poterne aggiungere un’altra.')).toBeVisible()
  await expect(page.getByText('15 / 15')).toBeVisible()
})
