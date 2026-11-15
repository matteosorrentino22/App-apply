import { useCallback, useState } from 'react'
import { useLanguage } from '../i18n/LanguageContext'
import { formatEuro } from '../utils/money'
import { Button } from '@/components/ui/button'
import { Modal, ModalActions, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'

// Conferma di un addebito a credito in una finestra dell'app (Sprint 74,
// SPEC-DELTA A11, mockup `confirm-cost`) al posto di `window.confirm`.
// Si chiede conferma solo quando la prossima richiesta andrebbe a credito
// (`next_charge = credit`, lib/usage.js); senza dati di
// consumo non si blocca (il backend applica comunque le regole).
//
//   const { confirmCost, costDialog } = useCostConfirm()
//   if (!(await confirmCost(usage, 'import'))) return
//   ... e {costDialog} nel JSX.
export function useCostConfirm() {
  const { t, lang } = useLanguage()
  const [pending, setPending] = useState(null)

  const confirmCost = useCallback((usage, actionKey) => {
    const action = usage?.actions?.[actionKey]
    if (!action || action.next_charge !== 'credit') return Promise.resolve(true)
    return new Promise((resolve) => setPending({ price: action.price, balance: usage.extra_credit, resolve }))
  }, [])

  function close(confirmed) {
    pending?.resolve(confirmed)
    setPending(null)
  }

  const costDialog = (
    <Modal open={pending !== null} onOpenChange={(open) => !open && close(false)}>
      <ModalContent>
        <ModalTitle>{t('usage.confirmTitle')}</ModalTitle>
        <ModalDescription className="text-[15px]">
          {pending
            ? t('usage.confirmCredit')
                .replace('{price}', formatEuro(pending.price, lang))
                .replace('{balance}', formatEuro(pending.balance, lang))
            : null}
        </ModalDescription>
        <ModalActions>
          <Button size="lg" onClick={() => close(true)}>
            {t('usage.confirmProceed')}
          </Button>
          <Button variant="text" onClick={() => close(false)}>
            {t('common.cancel')}
          </Button>
        </ModalActions>
      </ModalContent>
    </Modal>
  )

  return { confirmCost, costDialog }
}
