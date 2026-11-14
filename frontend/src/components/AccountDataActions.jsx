import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { deleteAccount, requestDataExport } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

// Export dei dati e cancellazione dell'account (Sprint 67): in Impostazioni
// e nella schermata di accettazione, perché entrambe le azioni restano
// disponibili anche a chi non ha (ancora) accettato informativa e termini.
export function ExportDataButton({ variant = 'secondary' }) {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const [busy, setBusy] = useState(false)

  async function handleExport() {
    setBusy(true)
    try {
      const url = await requestDataExport()
      window.location.assign(url)
    } catch (err) {
      showToast(err instanceof ApiError && err.status === 429 ? t('account.exportTooMany') : t('common.genericError'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Button type="button" variant={variant} disabled={busy} onClick={handleExport} className="w-fit">
      {busy ? t('account.exportPreparing') : t('account.exportButton')}
    </Button>
  )
}

export function DeleteAccountButton() {
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
      <Button type="button" variant="destructive" onClick={openDialog} className="w-fit">
        {t('account.deleteButton')}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('account.deleteDialogTitle')}</DialogTitle>
            <DialogDescription>
              {t('account.deleteDialogBody')}
              {legalInfo?.email_enabled && ` ${t('account.deleteDialogEmail')}`}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="delete-account-password">{t('account.deletePasswordLabel')}</Label>
              <Input
                id="delete-account-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </div>
            <label htmlFor="delete-account-confirm" className="flex items-start gap-2.5 text-sm">
              <Checkbox
                id="delete-account-confirm"
                className="mt-0.5"
                checked={confirmed}
                onCheckedChange={(checked) => setConfirmed(checked === true)}
              />
              <span>{t('account.deleteConfirmLabel')}</span>
            </label>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              {t('account.cancel')}
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={busy || !confirmed || !password}
              onClick={handleDelete}
            >
              {busy ? t('account.deleting') : t('account.deleteSubmit')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
