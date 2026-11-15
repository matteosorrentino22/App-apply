import { useLanguage } from '../../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Modal, ModalActions, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'

// "Bozza superata" (Sprint 69–70; dallo Sprint 76 `Modal`, mockup
// `cv-outdated`): stesse azioni di prima — ripartire dal nuovo documento
// (le modifiche e la chat si perdono) o continuare la bozza; chiudendo
// (Esc) si torna al job, come prima.
export default function OutdatedDraftModal({ title, hint, restartLabel, busy, onRestart, onContinue, onDismiss }) {
  const { t } = useLanguage()
  return (
    <Modal open onOpenChange={(open) => !open && onDismiss()}>
      <ModalContent>
        <ModalTitle>{title}</ModalTitle>
        <ModalDescription className="text-[15px]">{hint}</ModalDescription>
        <ModalActions>
          <Button size="lg" disabled={busy} onClick={onRestart}>
            {restartLabel}
          </Button>
          <Button variant="secondary" size="lg" disabled={busy} onClick={onContinue}>
            {t('cvEditor.outdatedContinue')}
          </Button>
        </ModalActions>
      </ModalContent>
    </Modal>
  )
}
