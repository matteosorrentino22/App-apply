import { useState } from 'react'
import { Check, Download, FileText, KeyRound } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useLanguage } from '../../i18n/LanguageContext'
import { changePassword } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useToast } from '@/components/ToastProvider'
import { DeleteAccountButton } from '@/components/AccountDataActions'
import { SettingsGroup, SettingsRow, SettingsSubpageHeader } from '@/components/settings/SettingsList'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import { useDataExport } from '@/lib/dataExport'

// Privacy e sicurezza (Sprint 78, sottopagina /settings/privacy, mockup
// `settings-privacy`, `settings-password`, `settings-delete`): cambio
// password in un pannello, documenti legali con versione e data accettate
// (anche la dichiarazione d'età), export dei dati, eliminazione dell'account.
// Stesse API e stesse regole di prima.

const EMPTY_PASSWORDS = { old: '', next: '', confirm: '' }

function PasswordSheet({ open, onOpenChange }) {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const [form, setForm] = useState(EMPTY_PASSWORDS)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function handleOpenChange(next) {
    if (next) {
      setForm(EMPTY_PASSWORDS)
      setError('')
    }
    onOpenChange(next)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (form.next !== form.confirm) {
      setError(t('account.passwordMismatch'))
      return
    }
    setBusy(true)
    try {
      await changePassword(form.old, form.next)
      setForm(EMPTY_PASSWORDS)
      showToast(t('account.passwordChanged'))
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError(t('common.tooManyRequests'))
      } else if (err instanceof ApiError && err.data && typeof err.data === 'object') {
        const first = Object.values(err.data).flat()[0]
        setError(typeof first === 'string' ? first : t('common.genericError'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent>
        <SheetHeader title={t('account.changePasswordTitle')} />
        <form id="password-form" onSubmit={handleSubmit} noValidate className="contents">
          <SheetBody className="pt-3">
            <Field label={t('account.oldPassword')}>
              <Input
                id="old-password"
                type="password"
                value={form.old}
                onChange={(e) => setForm({ ...form, old: e.target.value })}
                autoComplete="current-password"
              />
            </Field>
            <Field label={t('account.newPassword')} hint={t('settings.passwordHint')}>
              <Input
                id="new-password"
                type="password"
                value={form.next}
                onChange={(e) => setForm({ ...form, next: e.target.value })}
                autoComplete="new-password"
              />
            </Field>
            <Field label={t('account.confirmNewPassword')}>
              <Input
                id="confirm-new-password"
                type="password"
                value={form.confirm}
                onChange={(e) => setForm({ ...form, confirm: e.target.value })}
                autoComplete="new-password"
              />
            </Field>
            {error ? (
              <p role="alert" className="text-sm text-destructive-text">
                {error}
              </p>
            ) : null}
          </SheetBody>
          <SheetFooter>
            <Button type="submit" size="lg" form="password-form" disabled={busy || !form.old || !form.next}>
              {t('account.changePasswordSubmit')}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}

export default function PrivacyPage() {
  const { t, lang } = useLanguage()
  const { user } = useAuth()
  const { showToast } = useToast()
  const [passwordOpen, setPasswordOpen] = useState(false)
  const { busy: exporting, exportData } = useDataExport((key) => showToast(t(key)))

  if (!user) return null

  function formatDate(iso) {
    return new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(iso))
  }

  function acceptedLabel(document) {
    const acceptance = user.legal_acceptances?.[document]
    if (!acceptance) return null
    return t('account.acceptedOn').replace('{version}', acceptance.version).replace('{date}', formatDate(acceptance.accepted_at))
  }

  const age = user.legal_acceptances?.age

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-4 pb-6 pt-3 lg:pt-6">
      <SettingsSubpageHeader title={t('account.privacyTitle')} description={t('account.privacyHint')} />

      <SettingsGroup>
        <SettingsRow
          icon={KeyRound}
          title={t('account.changePasswordTitle')}
          subtitle={t('settings.passwordRowSubtitle')}
          onClick={() => setPasswordOpen(true)}
          testId="settings-password"
        />
      </SettingsGroup>

      <SettingsGroup title={t('account.legalDocsTitle')}>
        <SettingsRow icon={FileText} title={t('legal.privacy')} subtitle={acceptedLabel('privacy')} to="/privacy" />
        <SettingsRow icon={FileText} title={t('legal.terms')} subtitle={acceptedLabel('terms')} to="/terms" />
        {age ? (
          <SettingsRow
            icon={Check}
            title={t('settings.ageTitle')}
            subtitle={t('settings.ageAccepted').replace('{age}', age.version).replace('{date}', formatDate(age.accepted_at))}
          />
        ) : null}
      </SettingsGroup>

      <SettingsGroup title={t('settings.yourDataTitle')}>
        <SettingsRow
          icon={Download}
          title={exporting ? t('account.exportPreparing') : t('account.exportTitle')}
          subtitle={t('account.exportHint')}
          onClick={exporting ? undefined : exportData}
          testId="settings-export"
        />
      </SettingsGroup>

      <SettingsGroup title={t('account.dangerZoneTitle')} tone="danger">
        <div className="flex flex-col gap-3 p-4">
          <h3 className="text-[17px] font-bold text-destructive-text">{t('account.deleteTitle')}</h3>
          <p className="text-[15px] leading-normal text-muted-foreground">{t('account.deleteHint')}</p>
          <DeleteAccountButton fullWidth />
        </div>
      </SettingsGroup>

      <PasswordSheet open={passwordOpen} onOpenChange={setPasswordOpen} />
    </div>
  )
}
