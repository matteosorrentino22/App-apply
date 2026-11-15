import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { deleteAccount } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Field } from '@/components/ui/field'
import { Modal, ModalActions, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'
import { Trash2 } from 'lucide-react'

// Cancellazione dell'account (Sprint 67): in Impostazioni e nella schermata
// di accettazione, perché resta disponibile anche a chi non ha (ancora)
// accettato informativa e termini (l'export usa `useDataExport`, Sprint 78–79).
// Sprint 78: finestra di eliminazione come `Modal` (mockup `settings-delete`),
// stessi campi e stessa regola (password + spunta).
export function DeleteAccountButton({ fullWidth = false }) {
  const { t } = useLanguage()
  const { setUser } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const legalInfo = useLegalInfo()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function openDialog() {
    setPassword('')
    setConfirmed(false)
    setError('')
    setOpen(true)
  }

  async function handleDelete() {
    setError('')
    setBusy(true)
    try {
      await deleteAccount(password)
      setOpen(false)
      setUser(null)
      showToast(t('account.deleteDone'))
      navigate('/login', { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 400 && err.data?.password) {
        setError(t('account.wrongPassword'))
      } else if (err instanceof ApiError && err.status === 429) {
        setError(t('common.tooManyRequests'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Button
        type="button"
        variant="secondary"
        onClick={openDialog}
        className={fullWidth ? 'w-full border-destructive-border text-destructive-text hover:bg-destructive-soft' : 'w-fit border-destructive-border text-destructive-text hover:bg-destructive-soft'}
      >
        <Trash2 className="h-5 w-5" aria-hidden="true" />
        {t('account.deleteButton')}
      </Button>
      <Modal open={open} onOpenChange={(next) => !busy && setOpen(next)}>
        <ModalContent>
          <ModalTitle>{t('account.deleteDialogTitle')}</ModalTitle>
          <ModalDescription className="text-[15px]">
            {t('account.deleteDialogBody')}
            {legalInfo?.email_enabled && ` ${t('account.deleteDialogEmail')}`}
          </ModalDescription>
          <Field label={t('account.deletePasswordLabel')}>
            <Input
              id="delete-account-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </Field>
          <label htmlFor="delete-account-confirm" className="flex items-start gap-3 text-[15px] leading-snug">
            <Checkbox
              id="delete-account-confirm"
              className="mt-px"
              checked={confirmed}
              onCheckedChange={(checked) => setConfirmed(checked === true)}
            />
            <span>{t('account.deleteConfirmLabel')}</span>
          </label>
          {error && (
            <p role="alert" className="text-sm text-destructive-text">
              {error}
            </p>
          )}
          <ModalActions>
            <Button
              type="button"
              variant="destructive"
              size="lg"
              disabled={busy || !confirmed || !password}
              onClick={handleDelete}
            >
              {busy ? t('account.deleting') : t('account.deleteSubmit')}
            </Button>
            <Button type="button" variant="text" disabled={busy} onClick={() => setOpen(false)}>
              {t('account.cancel')}
            </Button>
          </ModalActions>
        </ModalContent>
      </Modal>
    </>
  )
}
