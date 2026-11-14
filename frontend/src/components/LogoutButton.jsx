import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Modal, ModalActions, ModalClose, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'

// "Esci" in fondo alle Impostazioni con finestra di conferma (Sprint 73,
// SPEC-DELTA A9; mockup `impostazioni`, finestra sul modello di
// `delete-search`). Stesso logout di prima (AuthContext): revoca il token di
// questo dispositivo e ne disattiva le notifiche push.
export default function LogoutButton() {
  const { logout } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleConfirm() {
    setBusy(true)
    try {
      await logout()
    } finally {
      setBusy(false)
      setOpen(false)
      navigate('/login')
    }
  }

  return (
    <Modal open={open} onOpenChange={(next) => !busy && setOpen(next)}>
      <Button
        variant="text"
        className="min-h-12 w-full text-base font-bold text-destructive-text hover:bg-destructive-soft"
        onClick={() => setOpen(true)}
      >
        <LogOut className="h-5 w-5" aria-hidden="true" />
        {t('account.logout')}
      </Button>
      <ModalContent>
        <ModalTitle>{t('account.logoutConfirmTitle')}</ModalTitle>
        <ModalDescription className="text-[15px]">{t('account.logoutConfirmBody')}</ModalDescription>
        <ModalActions>
          <Button variant="destructive" size="lg" onClick={handleConfirm} disabled={busy}>
            {t('account.logout')}
          </Button>
          <ModalClose asChild>
            <Button variant="text" disabled={busy}>
              {t('common.cancel')}
            </Button>
          </ModalClose>
        </ModalActions>
      </ModalContent>
    </Modal>
  )
}
