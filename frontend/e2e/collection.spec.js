import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '@playwright/test'

// Pannello "Raccogli nuovi job" (Sprint 77): una raccolta al giorno,
// automatica o manuale; raccolta automatica solo Pro, con orario.

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_DIR = path.resolve(__dirname, '../../backend')
const BACKEND_ENV = {
  ...process.env,
  DJANGO_SECRET_KEY: 'dev-insecure-secret-key',
  DJANGO_DEBUG: 'true',
  DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
  POSTGRES_HOST: 'localhost',
}
const INVITE_CODE = process.env.E2E_INVITE_CODE || ''

function python(args, input) {
  return execFileSync('.venv/bin/python', ['manage.py', ...args], { cwd: BACKEND_DIR, env: BACKEND_ENV, input }).toString()
}

let suffix = 0
async function loginNewUser(page, request, baseURL, { plan } = {}) {
  suffix += 1
  const email = `e2e-collect-${Date.now()}-${suffix}@example.com`
  const password = 'SuperSecret123!'
  await request.post(`${baseURL}/api/accounts/register/`, {
    data: { email, password, invite_code: INVITE_CODE, accept_privacy: true, accept_terms: true, confirm_age: true },
  })
  if (plan) python(['set_e2e_account', email, `--plan=${plan}`, '--credit=0'])
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Accedi', exact: true }).click()
  await page.waitForURL(/onboarding|list/)
  await page.goto('/list')
  return email
}

async function openSheet(page) {
  await page.getByRole('button', { name: 'Raccogli nuovi job' }).first().click()
  const sheet = page.getByRole('dialog', { name: 'Raccogli nuovi job' })
  await expect(sheet.getByRole('button', { name: 'Raccogli ora' })).toBeVisible()
  return sheet
}

test('Free: raccolta automatica bloccata con invito al Pro, regola di 1 al giorno', async ({ page, request, baseURL }) => {
  await loginNewUser(page, request, baseURL)
  const sheet = await openSheet(page)
  await expect(sheet.getByText('1 raccolta al giorno, automatica o manuale')).toBeVisible()
  await expect(sheet.getByRole('switch', { name: 'Raccolta automatica' })).toBeDisabled()
  await expect(sheet.getByRole('link', { name: 'Scopri il piano Pro' })).toHaveAttribute('href', '/settings')
  await expect(sheet.getByText('Orario di avvio')).toHaveCount(0)
})

test('Pro: attiva la raccolta automatica e sceglie l’orario, che resta dopo il ricaricamento', async ({
  page,
  request,
  baseURL,
}) => {
  await loginNewUser(page, request, baseURL, { plan: 'pro' })
  let sheet = await openSheet(page)
  const toggle = sheet.getByRole('switch', { name: 'Raccolta automatica' })
  await expect(toggle).toHaveAttribute('aria-checked', 'false')
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-checked', 'true')
  await expect(sheet.getByText('Ora italiana')).toBeVisible()
  const time = sheet.getByRole('combobox', { name: 'Orario di avvio' })
  await expect(time).toHaveText('07:00')
  await time.click()
  await page.getByRole('option', { name: '08:15' }).click()
  await expect(time).toHaveText('08:15')

  await page.reload()
  sheet = await openSheet(page)
  await expect(sheet.getByRole('switch', { name: 'Raccolta automatica' })).toHaveAttribute('aria-checked', 'true')
  await expect(sheet.getByRole('combobox', { name: 'Orario di avvio' })).toHaveText('08:15')
})

test('raccolta di oggi già fatta: "Raccogli ora" disattivato con l’ora', async ({ page, request, baseURL }) => {
  const email = await loginNewUser(page, request, baseURL, { plan: 'pro' })
  python(
    ['shell'],
    `
import datetime
from django.utils import timezone
from apps.accounts.models import User
from apps.jobs.models import DailyQuota
u = User.objects.get(email="${email}")
done = timezone.localtime().replace(hour=7, minute=0, second=0, microsecond=0)
if done > timezone.now():
    done = timezone.now()
DailyQuota.objects.update_or_create(user=u, date=timezone.localtime().date(), defaults={"collection_count": 1, "collection_done_at": done})
print("OK", done.strftime("%H:%M"))
`,
  )
  const sheet = await openSheet(page)
  await expect(sheet.getByRole('button', { name: 'Raccogli ora' })).toBeDisabled()
  await expect(sheet.getByTestId('collect-done')).toHaveText(/^Raccolta di oggi già eseguita alle \d{2}:\d{2}\.$/)
})
