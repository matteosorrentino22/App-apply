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
  await page.getByRole('button', { name: 'Registrati' }).click()

  await expect(page).toHaveURL(/\/onboarding$/)

  // Step 1: preferenze
  await page.getByRole('button', { name: 'Avanti' }).click()
  await expect(page.getByText('Profilo', { exact: true })).toBeVisible()

  // Step 2: profilo compilato manualmente (nessun upload CV, per non dipendere da Claude)
  await page.getByLabel('Sommario professionale').fill('Sviluppatore software con 5 anni di esperienza.')
  await page.getByRole('button', { name: 'Salva profilo' }).click()

  await expect(page.getByText('Crea la tua prima ricerca')).toBeVisible()

  // Step 3: prima ricerca
  await page.getByLabel('Nome ricerca').fill('Ricerca test')
  await page.getByLabel('Parole chiave').fill('developer')
  await page.getByLabel('Località').fill('Milano')
  await page.getByRole('button', { name: 'Vai alla lista' }).click()

  await expect(page).toHaveURL(/\/list$/)
  await expect(page.getByRole('heading', { name: 'I tuoi job' })).toBeVisible()

  expect(consoleErrors, `Errori console rilevati: ${consoleErrors.join('\n')}`).toHaveLength(0)
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

    await page.getByLabel('Lingua / Language').selectOption('it')
    await expect(page.getByRole('heading', { name: 'Accedi' })).toBeVisible()
  })
})
