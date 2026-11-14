import { existsSync } from 'node:fs'
import { defineConfig } from '@playwright/test'

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
    launchOptions: chromiumPath ? { executablePath: chromiumPath } : {},
  },
})
