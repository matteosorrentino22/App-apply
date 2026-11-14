import { useCallback, useEffect, useState } from 'react'
import { fetchUsage } from '../api/usage'
import { formatEuro } from '../utils/money'

// Contatori e prezzi visibili (Sprint 70, §4.11 funzionali), condivisi da
// tutti i punti in cui un'azione consuma massimale o credito: `useUsage`
// legge GET /api/accounts/usage/, `actionCostText` descrive cosa succede
// alla prossima richiesta (componente `ActionCostHint`),
// `confirmCreditCharge` chiede conferma quando la richiesta andrebbe a
// credito. Chiavi delle azioni come nel backend: cv, cover_letter,
// referral_message, import, manual_job, collection, cv_import; prezzi delle
// chat in `usage.chat_prices`.

export function useUsage() {
  const [usage, setUsage] = useState(null)

  const refresh = useCallback(() => {
    return fetchUsage()
      .then((data) => {
        setUsage(data)
        return data
      })
      .catch(() => null)
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { usage, refresh }
}

function fill(template, values) {
  return Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`{${key}}`, value), template)
}

export function actionCostText(t, lang, usage, actionKey) {
  const action = usage?.actions?.[actionKey]
  if (!action) return ''
  const values = {
    used: action.used,
    limit: action.limit,
    remaining: action.remaining,
    price: action.price != null ? formatEuro(action.price, lang) : '',
    balance: formatEuro(usage.extra_credit, lang),
  }
  switch (action.next_charge) {
    case 'included':
      return fill(t('usage.hintIncluded'), values)
    case 'credit':
      return fill(t('usage.hintCredit'), values)
    case 'blocked':
      return fill(t(action.price != null ? 'usage.hintBlockedCredit' : 'usage.hintBlockedNoCredit'), values)
    default:
      return ''
  }
}

// true se si può procedere: nessun addebito a credito previsto, oppure
// l'utente ha confermato il prezzo. Senza dati (usage non ancora caricato)
// non blocca: il backend applica comunque le regole.
export function confirmCreditCharge(t, lang, usage, actionKey) {
  const action = usage?.actions?.[actionKey]
  if (!action || action.next_charge !== 'credit') return true
  return window.confirm(
    fill(t('usage.confirmCredit'), {
      price: formatEuro(action.price, lang),
      balance: formatEuro(usage.extra_credit, lang),
    }),
  )
}
