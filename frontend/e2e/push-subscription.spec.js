import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'

// Il flusso reale di sottoscrizione richiede un service worker attivo, che
// esiste solo nella build di produzione (`vite preview`), non nel dev server
// (devOptions.enabled: false in vite.config.js, per non interferire con
// l'HMR — vedi Sprint 20). Serve quindi un server dedicato in preview.
test.use({ baseURL: process.env.E2E_PREVIEW_BASE_URL || 'http://localhost:5174' })

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_DIR = path.resolve(__dirname, '../../backend')
const BACKEND_ENV = {
  ...process.env,
  DJANGO_SECRET_KEY: 'dev-insecure-secret-key',
  DJANGO_DEBUG: 'true',
  DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
  POSTGRES_HOST: 'localhost',
}

function pushSubscriptionExists(email, endpoint) {
  const script = [
    'from apps.accounts.models import User',
    'from apps.notifications.models import PushSubscription',
    `u = User.objects.get(email="${email}")`,
    `print(PushSubscription.objects.filter(user=u, endpoint="${endpoint}").exists())`,
  ].join('\n')
  const output = execFileSync('.venv/bin/python', ['manage.py', 'shell', '-c', script], {
    cwd: BACKEND_DIR,
    env: BACKEND_ENV,
  })
  return output.toString().trim() === 'True'
}

let uniqueSuffix = 0
async function registerUser(request, baseURL) {
  uniqueSuffix += 1
  const email = `e2e-push-${Date.now()}-${uniqueSuffix}@example.com`
  const password = 'SuperSecret123!'
  const response = await request.post(`${baseURL}/api/accounts/register/`, {
    data: { email, password },
  })
  const body = await response.json()
  return { email, password, token: body.token }
}

// Chromium non supporta la vera Push API dentro un contesto browser isolato
// come quelli creati da Playwright (trattati come "incognito"): è una
// limitazione nota della piattaforma (crbug.com/401439), non testabile.
// Si mocka quindi solo l'API nativa (Notification.requestPermission,
// PushManager.subscribe), mantenendo reale il service worker della build di
// produzione, per verificare il codice di integrazione scritto per Sprint 20.
const FAKE_ENDPOINT = 'https://fake-push.example.com/abc123'

async function mockPushApi(page) {
  await page.addInitScript((endpoint) => {
    window.Notification.requestPermission = async () => 'granted'
    if (window.PushManager) {
      window.PushManager.prototype.getSubscription = async () => null
      window.PushManager.prototype.subscribe = async () => ({
        endpoint,
        toJSON() {
          return { endpoint, keys: { p256dh: 'fake-p256dh-key', auth: 'fake-auth-key' } }
        },
      })
    }
  }, FAKE_ENDPOINT)
}

test('completando il flusso di sottoscrizione viene creata una PushSubscription verificabile lato backend', async ({
  page,
  request,
  baseURL,
}) => {
  const { email, password } = await registerUser(request, baseURL)
  await mockPushApi(page)

  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()
  await page.waitForURL(/onboarding|list/)
  await page.goto('/account')

  await page.getByRole('button', { name: 'Attiva notifiche' }).click()
  await expect(page.getByText('Notifiche attive su questo dispositivo.')).toBeVisible()

  expect(pushSubscriptionExists(email, FAKE_ENDPOINT)).toBe(true)
})
