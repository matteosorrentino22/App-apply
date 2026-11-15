import { existsSync } from 'node:fs'
import { defineConfig, devices } from '@playwright/test'

// Chromium preinstallato dell'ambiente in cui la suite è nata; altrove (es.
// un computer di sviluppo dopo `npx playwright install chromium`) Playwright
// usa il proprio browser. PW_CHROMIUM_PATH permette di indicarne un altro.
const PRESET_CHROMIUM = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
const chromiumPath = process.env.PW_CHROMIUM_PATH || (existsSync(PRESET_CHROMIUM) ? PRESET_CHROMIUM : undefined)

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    locale: 'it-IT',
  },
  // Sprint 81: tutti gli spec in Chromium; lo spec di impaginazione anche in
  // WebKit con l'emulazione di iPhone (Safari rende diversamente, ad esempio,
  // i campi data). `npx playwright test --project=chromium` per il solo Chromium.
  projects: [
    { name: 'chromium', use: { browserName: 'chromium', launchOptions: chromiumPath ? { executablePath: chromiumPath } : {} } },
    { name: 'iphone-13', use: { ...devices['iPhone 13'], locale: 'it-IT' }, testMatch: /layout\.spec\.js/ },
    { name: 'iphone-se', use: { ...devices['iPhone SE'], locale: 'it-IT' }, testMatch: /layout\.spec\.js/ },
  ],
})
