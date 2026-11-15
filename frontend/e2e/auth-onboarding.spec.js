import { test, expect } from '@playwright/test'

function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 10000)}@example.com`
}

test('registrazione, onboarding manuale e arrivo alla lista senza errori console', async ({ page }) => {
  // Il probe iniziale "sono loggato?" (AuthProvider) genera un 401 atteso e
  // gestito (utente non ancora autenticato): il browser lo logga comunque
  // come "Failed to load resource", ma non è un errore applicativo - va
  // escluso dal controllo, che qui punta a rilevare eccezioni JS reali.
  const consoleErrors = []
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !msg.text().includes('401')) consoleErrors.push(msg.text())
  })
  page.on('pageerror', (err) => consoleErrors.push(String(err)))

  const email = uniqueEmail()
  const password = 'SuperSecret123!'

  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  // Sprint 67: informativa, termini ed età minima (tre spunte obbligatorie).
  for (const box of await page.getByRole('checkbox').all()) await box.click()
  // Sprint 66: codice di invito, se il backend di prova lo richiede.
  if (process.env.E2E_INVITE_CODE) await page.getByLabel('Codice di invito').fill(process.env.E2E_INVITE_CODE)
  await page.getByRole('button', { name: 'Registrati' }).click()

  await expect(page).toHaveURL(/\/onboarding$/)

  // Step 1: preferenze (Nome e Cognome obbligatori dallo Sprint 32)
  await page.getByLabel('Nome', { exact: true }).fill('Mario')
  await page.getByLabel('Cognome').fill('Rossi')
  await page.getByRole('button', { name: 'Avanti' }).click()
  // Sprint 79: indicatore dei passi a barre; il passo corrente ha aria-current.
  await expect(page.getByRole('heading', { name: 'Il tuo profilo', level: 1 })).toBeVisible()
  await expect(page.locator('[aria-current="step"]')).toHaveText('Profilo')

  // Step 2: profilo compilato manualmente (nessun upload CV, per non dipendere da Claude)
  await page.getByLabel('Sommario professionale').fill('Sviluppatore software con 5 anni di esperienza.')
  // Città e Paese del profilo: il campo con suggerimenti li richiede (vedi
  // sprints/sprint-73.md, segnalazione sulla città del profilo obbligatoria).
  await page.getByLabel('Città', { exact: true }).fill('Milano')
  await page.getByLabel('Paese', { exact: true }).fill('Italia')
  await page.getByRole('button', { name: 'Salva profilo' }).click()

  await expect(page.getByText('Crea la tua prima ricerca')).toBeVisible()

  // Step 3: prima ricerca
  await page.getByLabel('Parole chiave').fill('developer')
  await page.getByLabel('Città', { exact: true }).fill('Milano')
  await page.getByLabel('Paese', { exact: true }).fill('Italia')
  await page.getByRole('button', { name: 'Vai alla lista' }).click()

  await expect(page).toHaveURL(/\/list$/)
  await expect(page.getByRole('heading', { name: 'Jobs', level: 1 })).toBeVisible()

  expect(consoleErrors, `Errori console rilevati: ${consoleErrors.join('\n')}`).toHaveLength(0)
})

test('esperienze: più ruoli nella stessa azienda restano un unico gruppo in UI', async ({ page }) => {
  const email = uniqueEmail()
  const password = 'SuperSecret123!'
  console.log('EXPERIENCE_TEST_EMAIL=' + email)

  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  // Sprint 67: informativa, termini ed età minima (tre spunte obbligatorie).
  for (const box of await page.getByRole('checkbox').all()) await box.click()
  // Sprint 66: codice di invito, se il backend di prova lo richiede.
  if (process.env.E2E_INVITE_CODE) await page.getByLabel('Codice di invito').fill(process.env.E2E_INVITE_CODE)
  await page.getByRole('button', { name: 'Registrati' }).click()
  await expect(page).toHaveURL(/\/onboarding$/)

  // Nome e Cognome obbligatori dallo Sprint 32.
  await page.getByLabel('Nome', { exact: true }).fill('Mario')
  await page.getByLabel('Cognome').fill('Rossi')
  await page.getByRole('button', { name: 'Avanti' }).click()
  // Sprint 79: indicatore dei passi a barre; il passo corrente ha aria-current.
  await expect(page.getByRole('heading', { name: 'Il tuo profilo', level: 1 })).toBeVisible()
  await expect(page.locator('[aria-current="step"]')).toHaveText('Profilo')

  await page.getByRole('button', { name: 'Aggiungi azienda' }).click()
  await page.getByLabel('Azienda').fill('Acme Srl')

  const roleInputs = page.getByLabel('Ruolo', { exact: true })
  const locationInputs = page.getByLabel('Località', { exact: true })
  await roleInputs.nth(0).fill('Team Lead')
  await locationInputs.nth(0).fill('Roma')

  const chipInputs = page.getByLabel('Attività / competenze in questo ruolo')
  await chipInputs.nth(0).fill('Coordinamento team')
  await chipInputs.nth(0).press('Enter')
  await chipInputs.nth(0).fill('Onboarding nuovi assunti')
  await chipInputs.nth(0).press('Enter')

  await page.getByRole('button', { name: 'Aggiungi un altro ruolo in questa azienda' }).click()
  await roleInputs.nth(1).fill('Project Manager')
  await locationInputs.nth(1).fill('Milano')
  await chipInputs.nth(1).fill('Gestione stakeholder')
  await chipInputs.nth(1).press('Enter')

  // Un solo campo "Azienda" per i due ruoli: conferma che è un gruppo unico, non due righe indipendenti.
  await expect(page.getByLabel('Azienda')).toHaveCount(1)
  await expect(page.getByText('Coordinamento team')).toBeVisible()
  await expect(page.getByText('Gestione stakeholder')).toBeVisible()

  // Città e Paese del profilo: il campo con suggerimenti li richiede (vedi
  // sprints/sprint-73.md, segnalazione sulla città del profilo obbligatoria).
  await page.getByLabel('Città', { exact: true }).fill('Milano')
  await page.getByLabel('Paese', { exact: true }).fill('Italia')
  await page.getByRole('button', { name: 'Salva profilo' }).click()
  await expect(page.getByText('Crea la tua prima ricerca')).toBeVisible()
})

test('login con credenziali errate mostra un errore e non naviga oltre', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('nonexistent-user@example.com')
  await page.getByLabel('Password').fill('wrong-password')
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()

  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
})

test.describe('lingua da dispositivo', () => {
  test.use({ locale: 'it-IT' })
  test('un browser italiano mostra l\'interfaccia in italiano', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Accedi' })).toBeVisible()
  })
})

test.describe('lingua da dispositivo (non italiano)', () => {
  test.use({ locale: 'en-US' })
  test('un browser non italiano mostra l\'interfaccia in inglese', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
  })
})

test.describe('cambio lingua manuale', () => {
  test.use({ locale: 'en-US' })
  test('la lingua è modificabile tramite lo switcher', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()

    await page.getByRole('combobox', { name: 'Lingua / Language' }).click()
    await page.getByRole('option', { name: 'IT' }).click()
    await expect(page.getByRole('heading', { name: 'Accedi' })).toBeVisible()
  })
})

// --- Sprint 79: accesso, onboarding, legale (mockup `login-not-verified`,
// `register-err`, `verify-ok`, `verify-expired`, `forgot-sent`,
// `reset-invalid`, `reset-done`, `onboarding2-err`, `legal-gate`,
// `legal-privacy`, `legal-terms`). Gli stati che dipendono dall'email
// (link di verifica e di reset, account non confermato) sono simulati con
// risposte finte dell'API: nello stack di prova le email non partono.

async function registerNewUser(page) {
  const email = uniqueEmail()
  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill('SuperSecret123!')
  for (const box of await page.getByRole('checkbox').all()) await box.click()
  if (process.env.E2E_INVITE_CODE) await page.getByLabel('Codice di invito').fill(process.env.E2E_INVITE_CODE)
  await page.getByRole('button', { name: 'Registrati' }).click()
  await expect(page).toHaveURL(/\/onboarding$/)
  return email
}

test('onboarding: passi, fuso orario e import del CV con errore e riprova', async ({ page }) => {
  await registerNewUser(page)
  await expect(page.locator('[aria-current="step"]')).toHaveText('Preferenze')
  await expect(page.getByLabel('Fuso orario')).toBeVisible()
  await page.getByLabel('Nome', { exact: true }).fill('Mario')
  await page.getByLabel('Cognome').fill('Rossi')
  await page.getByRole('button', { name: 'Avanti' }).click()
  await expect(page.locator('[aria-current="step"]')).toHaveText('Profilo')

  let calls = 0
  await page.route('**/api/profile/import-cv/', (route) => {
    calls += 1
    if (calls === 1) return route.fulfill({ status: 422, contentType: 'application/json', body: '{}' })
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: 'Sommario letto dal CV',
        phone: '',
        email: '',
        experiences: [],
        educations: [],
        skills: [],
        certifications: [],
        languages: [],
      }),
    })
  })
  const file = { name: 'cv.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4 prova') }
  // Il riquadro ha lo stesso nome del campo: si prende l'input del file.
  const input = page.locator('input[type="file"][accept=".pdf,.docx"]')
  await input.setInputFiles(file)
  await expect(page.getByText('Non siamo riusciti a leggere il CV')).toBeVisible()
  await expect(page.getByText('Puoi anche riprovare con un altro file.')).toBeVisible()
  // Riprova con lo stesso file: il campo viene svuotato dopo ogni scelta.
  await input.setInputFiles(file)
  await expect(page.getByLabel('Sommario professionale')).toHaveValue('Sommario letto dal CV')
  await expect(page.getByText('Non siamo riusciti a leggere il CV')).toHaveCount(0)
  expect(calls).toBe(2)
})

test('registrazione: errori dei campi in linea e consensi obbligatori', async ({ page }) => {
  await page.goto('/register')
  await page.getByLabel('Email').fill(uniqueEmail())
  await page.getByLabel('Password').fill('SuperSecret123!')
  await page.getByRole('button', { name: 'Registrati' }).click()
  // Senza le tre spunte la richiesta non parte: messaggio sotto i consensi.
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page).toHaveURL(/\/register$/)

  await page.route('**/api/accounts/register/', (route) =>
    route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ invite_code: ['Codice di invito non valido.'], password: ['Password troppo comune.'] }),
    }),
  )
  for (const box of await page.getByRole('checkbox').all()) await box.click()
  await page.getByRole('button', { name: 'Registrati' }).click()
  await expect(page.getByText('Codice di invito non valido.')).toBeVisible()
  await expect(page.getByText('Password troppo comune.')).toBeVisible()
  await expect(page.getByLabel('Codice di invito')).toHaveAttribute('aria-invalid', 'true')
})

test('registrazione riuscita con verifica email: schermata "controlla la tua email"', async ({ page }) => {
  await page.route('**/api/accounts/register/', (route) =>
    route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ verification_required: true }) }),
  )
  await page.goto('/register')
  await page.getByLabel('Email').fill(uniqueEmail())
  await page.getByLabel('Password').fill('SuperSecret123!')
  for (const box of await page.getByRole('checkbox').all()) await box.click()
  if (process.env.E2E_INVITE_CODE) await page.getByLabel('Codice di invito').fill(process.env.E2E_INVITE_CODE)
  await page.getByRole('button', { name: 'Registrati' }).click()
  await expect(page.getByRole('link', { name: 'Vai all’accesso' })).toBeVisible()
})

test('login con email non confermata: avviso e "Invia di nuovo il link"', async ({ page }) => {
  await page.route('**/api/accounts/login/', (route) =>
    route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ code: 'email_not_verified' }) }),
  )
  await page.route('**/api/accounts/verify-email/resend/', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/login')
  await expect(page.getByRole('button', { name: /google/i })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Password dimenticata?' })).toBeVisible()
  await page.getByLabel('Email').fill('in-attesa@example.com')
  await page.getByLabel('Password').fill('SuperSecret123!')
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()
  await expect(page.getByText('Devi prima confermare il tuo indirizzo email')).toBeVisible()
  await page.getByRole('button', { name: 'Invia di nuovo il link' }).click()
  await expect(page.getByText('ti abbiamo inviato un nuovo link')).toBeVisible()
})

test('verifica email: link riuscito, scaduto e mancante', async ({ page }) => {
  await page.route('**/api/accounts/verify-email/', (route) => {
    const token = route.request().postDataJSON().token
    if (token === 'ok') return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    return route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ code: 'expired' }) })
  })
  await page.goto('/verify-email?t=ok')
  await expect(page.getByText('Indirizzo confermato. Ora puoi accedere.')).toBeVisible()
  await page.goto('/verify-email?t=vecchio')
  await expect(page.getByText('Il link è scaduto.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Invia un nuovo link' })).toBeVisible()
  await page.goto('/verify-email')
  await expect(page.getByText('Il link non è valido.')).toBeVisible()
})

test('password dimenticata: senza invio email la funzione è indicata come non disponibile', async ({ page }) => {
  // Nello stack di prova l'invio email non è configurato (come nell'anteprima).
  await page.goto('/forgot-password')
  await expect(page.getByText('non è al momento disponibile')).toBeVisible()
  await expect(page.getByLabel('Email')).toHaveCount(0)
})

test('password dimenticata e reset: invio, link non valido, esito', async ({ page }) => {
  // Simula un server con l'invio email configurato.
  await page.route('**/api/legal/', async (route) => {
    const response = await route.fetch()
    await route.fulfill({ response, json: { ...(await response.json()), email_enabled: true } })
  })
  await page.route('**/api/accounts/password-reset/', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/login')
  await page.getByRole('link', { name: 'Password dimenticata?' }).click()
  await expect(page).toHaveURL(/\/forgot-password$/)
  await page.getByLabel('Email').fill('qualcuno@example.com')
  await page.getByRole('button', { name: 'Invia il link' }).click()
  await expect(page.getByText('Se l’indirizzo corrisponde a un account')).toBeVisible()
  await expect(page.getByLabel('Email')).toHaveCount(0)

  await page.goto('/reset-password')
  await expect(page.getByText('Il link non è valido o è scaduto')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Chiedi un nuovo link' })).toBeVisible()

  await page.route('**/api/accounts/password-reset/confirm/', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
  )
  await page.goto('/reset-password?uid=x&token=y')
  await page.getByLabel('Nuova password', { exact: true }).fill('NuovaPassword123!')
  await page.getByLabel('Ripeti la nuova password').fill('NuovaPassword123!')
  await page.getByRole('button', { name: 'Salva la nuova password' }).click()
  await expect(page.getByText('Password aggiornata.')).toBeVisible()
})

test('pagine legali: sezioni a fisarmonica, la prima aperta', async ({ page }) => {
  await page.goto('/privacy')
  const privacy = page.getByRole('main').locator('details')
  await expect(privacy).toHaveCount(12)
  await expect(privacy.first()).toHaveAttribute('open', '')
  await expect(privacy.nth(1)).not.toHaveAttribute('open', '')
  await privacy.nth(1).locator('summary').click()
  await expect(privacy.nth(1)).toHaveAttribute('open', '')
  await page.goto('/terms')
  await expect(page.getByRole('main').locator('details')).toHaveCount(11)
})

test('accettazione di informativa e termini: Continua solo con le tre spunte', async ({ page }) => {
  await registerNewUser(page)
  // Simula una nuova versione dei documenti: /me/ chiede la riaccettazione.
  await page.route('**/api/accounts/me/', async (route) => {
    if (route.request().method() !== 'GET') return route.continue()
    const response = await route.fetch()
    const body = await response.json()
    await route.fulfill({ response, json: { ...body, legal_acceptance_required: true } })
  })
  await page.goto('/list')
  await expect(page.getByRole('heading', { name: 'Informativa privacy e termini di servizio' })).toBeVisible()
  const submit = page.getByRole('button', { name: 'Continua' })
  await expect(submit).toBeDisabled()
  const boxes = page.getByRole('main').getByRole('checkbox')
  await expect(boxes).toHaveCount(3)
  for (const box of await boxes.all()) await box.click()
  await expect(submit).toBeEnabled()
  await expect(page.getByRole('button', { name: 'Elimina account' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Esci' })).toBeVisible()
})
