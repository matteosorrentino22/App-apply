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

let uniqueSuffix = 0
async function registerUser(request, baseURL) {
  uniqueSuffix += 1
  const email = `e2e-acc-${Date.now()}-${uniqueSuffix}@example.com`
  const password = 'SuperSecret123!'
  const response = await request.post(`${baseURL}/api/accounts/register/`, {
    data: { email, password },
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
  await page.goto('/account')
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

test('crea, attiva, disattiva ed elimina una ricerca salvata', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)

  await page.getByLabel('Nome ricerca').fill('PM Milano')
  await page.getByLabel('Parole chiave').fill('project manager')
  await page.getByLabel('Località').fill('Milano')
  await page.getByRole('button', { name: 'Aggiungi ricerca' }).click()

  await expect(page.getByText('project manager · Milano')).toBeVisible()

  await page.getByRole('button', { name: 'Attiva', exact: true }).click()
  await expect(page.getByText('In uso')).toBeVisible()

  await page.getByRole('button', { name: 'Disattiva' }).click()
  await expect(page.getByText('In uso')).not.toBeVisible()

  await page.getByRole('button', { name: 'Elimina' }).click()
  await expect(page.getByText('project manager · Milano')).not.toBeVisible()
  await expect(page.getByText('Nessuna ricerca salvata.')).toBeVisible()
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
      data: { name: `Ricerca ${i}`, keywords: 'developer', location: 'Roma' },
    })
  }

  await login(page, email, password)

  await page.getByLabel('Nome ricerca').fill('Undicesima')
  await page.getByLabel('Parole chiave').fill('developer')
  await page.getByLabel('Località').fill('Roma')
  await page.getByRole('button', { name: 'Aggiungi ricerca' }).click()

  await expect(
    page.getByText('Hai raggiunto il numero massimo di ricerche salvate per il tuo piano.'),
  ).toBeVisible()
})

test('le impostazioni persistono dopo il reload della pagina', async ({ page, request, baseURL }) => {
  const { email, password } = await registerUser(request, baseURL)
  await login(page, email, password)

  await page.getByText('Sempre in inglese').click()
  await page.getByLabel('Includi la foto nel CV').check()
  await expect(page.getByText('Impostazioni salvate.')).toBeVisible()

  await page.reload()

  await expect(page.getByRole('radio', { name: 'Sempre in inglese' })).toBeChecked()
  await expect(page.getByLabel('Includi la foto nel CV')).toBeChecked()
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
