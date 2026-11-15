import { useEffect, useState } from 'react'
import { FileText, Gauge, Globe, ImageIcon, Languages, Lock, Mail, RefreshCw, Search, Shield } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useLanguage } from '../../i18n/LanguageContext'
import { updateMe } from '../../api/auth'
import { fetchSearches } from '../../api/searches'
import { ApiError } from '../../api/client'
import { SUPPORTED_LANGUAGES } from '../../i18n/translations'
import { useToast } from '@/components/ToastProvider'
import EmailChangeForm from '@/components/EmailChangeForm'
import LogoutButton from '@/components/LogoutButton'
import TimezoneSelect from '@/components/TimezoneSelect'
import NotificationsRow from '@/components/settings/NotificationsRow'
import { SettingsGroup, SettingsRow } from '@/components/settings/SettingsList'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { QUARTER_HOURS, timeZoneLabel } from '../../utils/collection'

// Impostazioni (Sprint 78, mockup `impostazioni`): elenco a gruppi al posto
// della pagina unica `AccountPage` (Sprint 20–77). Ricerche, limiti di oggi e
// privacy sono sottopagine con route proprie (/settings/searches,
// /settings/limits, /settings/privacy); lingua del CV, email, fuso orario e
// lingua dell'interfaccia sono pannelli dal basso; raccolta automatica
// (Sprint 77), foto nel CV e notifiche sono interruttori nell'elenco. Stesse
// API di prima (PATCH /api/accounts/me/ e le altre).

function formatCredit(value) {
  const amount = Number(value ?? 0)
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)
}

function OptionList({ name, value, options, onChange }) {
  return (
    <RadioGroup value={value} onValueChange={onChange} className="flex flex-col gap-2.5" name={name}>
      {options.map((option) => (
        <label
          key={option.value}
          className={cn(
            'flex min-h-14 cursor-pointer items-center gap-3 rounded-field border px-4 py-3 text-base font-semibold',
            value === option.value ? 'border-primary bg-tint' : 'border-input bg-card',
          )}
        >
          <RadioGroupItem value={option.value} />
          {option.label}
        </label>
      ))}
    </RadioGroup>
  )
}

function ChoiceSheet({ open, onOpenChange, title, description, name, value, options, onChange }) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader title={title} description={description} />
        <SheetBody className="pt-3">
          <OptionList
            name={name}
            value={value}
            options={options}
            onChange={(next) => {
              onChange(next)
              onOpenChange(false)
            }}
          />
        </SheetBody>
      </SheetContent>
    </Sheet>
  )
}

export default function SettingsPage() {
  const { t, lang, setLang } = useLanguage()
  const { user, refreshUser } = useAuth()
  const { showToast } = useToast()
  const [searches, setSearches] = useState(null)
  const [sheet, setSheet] = useState(null)
  // Stato ottimistico (come prima): il controllo risponde subito al tocco.
  const [cvLanguageMode, setCvLanguageMode] = useState(user?.cv_language_mode)
  const [cvIncludePhoto, setCvIncludePhoto] = useState(user?.cv_include_photo ?? false)
  const [notificationsEnabled, setNotificationsEnabled] = useState(user?.notifications_enabled ?? true)
  const [timeZone, setTimeZone] = useState(user?.timezone || 'Europe/Rome')
  const [savingAuto, setSavingAuto] = useState(false)

  useEffect(() => {
    fetchSearches()
      .then(setSearches)
      .catch(() => setSearches([]))
  }, [])

  async function handleSettingChange(patch) {
    try {
      await updateMe(patch)
      await refreshUser()
      showToast(t('account.settingsSaved'))
      return true
    } catch (err) {
      const detail = err instanceof ApiError ? Object.values(err.data || {}).flat()[0] : null
      showToast(typeof detail === 'string' ? detail : t('common.genericError'))
      return false
    }
  }

  async function handleAutoChange(patch) {
    setSavingAuto(true)
    await handleSettingChange(patch)
    setSavingAuto(false)
  }

  async function handleNotificationsPreference(enabled) {
    setNotificationsEnabled(enabled)
    await handleSettingChange({ notifications_enabled: enabled })
  }

  if (!user) return null

  const isPro = user.plan === 'pro'
  const activeSearches = (searches || []).filter((search) => search.is_active).length
  const searchesSubtitle =
    searches == null
      ? ''
      : activeSearches === 0
        ? t('settings.searchesNoneActive')
        : activeSearches === 1
          ? t('settings.searchesOneActive')
          : t('settings.searchesManyActive').replace('{count}', activeSearches)
  const autoOn = isPro && user.auto_collection_enabled
  const autoTime = user.auto_collection_time || '07:00'
  const cvLanguageOptions = [
    { value: 'job_language', label: t('onboarding.cvLanguageJob') },
    { value: 'english', label: t('onboarding.cvLanguageEnglish') },
  ]
  const interfaceOptions = SUPPORTED_LANGUAGES.map((code) => ({ value: code, label: t(`settings.languageName_${code}`) }))

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-4 pb-6 pt-5 lg:pt-8">
      <h1 className="text-[28px] font-bold leading-tight tracking-[-0.01em] text-foreground">{t('account.title')}</h1>

      <section
        aria-label={t('account.planTitle')}
        className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 rounded-card bg-primary px-5 py-4 text-primary-foreground shadow-card"
      >
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.08em] opacity-80">{t('settings.planLabel')}</p>
          <p className="text-2xl font-bold">{t(`account.plan_${user.plan}`)}</p>
        </div>
        <div className="text-right">
          <p className="text-sm opacity-80">{t('account.creditBalance')}</p>
          <p className="text-2xl font-bold tabular-nums">{formatCredit(user.extra_credit)}</p>
        </div>
        <p className="w-full text-xs opacity-80">{t('account.creditHint')}</p>
      </section>

      <SettingsGroup title={t('settings.groupSearch')}>
        <SettingsRow icon={Search} title={t('account.searchesTitle')} subtitle={searchesSubtitle} to="/settings/searches" testId="settings-searches" />
        <SettingsRow
          icon={RefreshCw}
          title={
            <span className="flex flex-wrap items-center gap-2">
              {t('home.autoCollectTitle')}
              {isPro ? null : (
                <Badge variant="neutral" className="gap-1 text-xs">
                  <Lock className="h-3 w-3" aria-hidden="true" />
                  PRO
                </Badge>
              )}
            </span>
          }
          subtitle={
            !isPro
              ? t('settings.autoCollectProOnly')
              : autoOn
                ? `${t('settings.autoCollectAt').replace('{time}', autoTime)} · ${timeZoneLabel(t, user.timezone)}`
                : t('settings.autoCollectOff')
          }
          testId="settings-auto-collection"
          trailing={
            <Switch
              checked={autoOn}
              disabled={!isPro || savingAuto}
              label={t('home.autoCollectTitle')}
              onCheckedChange={(checked) => handleAutoChange({ auto_collection_enabled: checked })}
            />
          }
        >
          {autoOn ? (
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-semibold text-foreground" id="settings-auto-time-label">
                {t('home.autoCollectTimeLabel')}
              </span>
              <Select value={autoTime} disabled={savingAuto} onValueChange={(value) => handleAutoChange({ auto_collection_time: value })}>
                <SelectTrigger aria-labelledby="settings-auto-time-label" className="w-32 font-bold">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {QUARTER_HOURS.map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}
          {!isPro ? <p className="mt-1 text-sm text-muted-foreground">{t('home.autoCollectProPitch')}</p> : null}
        </SettingsRow>
      </SettingsGroup>

      <SettingsGroup title={t('settings.groupDocuments')}>
        <SettingsRow
          icon={FileText}
          title={t('onboarding.cvLanguageLabel')}
          subtitle={cvLanguageOptions.find((option) => option.value === cvLanguageMode)?.label}
          onClick={() => setSheet('cvLanguage')}
          testId="settings-cv-language"
        />
        <SettingsRow
          icon={ImageIcon}
          title={t('onboarding.cvIncludePhotoLabel')}
          trailing={
            <Switch
              checked={cvIncludePhoto}
              label={t('onboarding.cvIncludePhotoLabel')}
              onCheckedChange={(checked) => {
                setCvIncludePhoto(checked)
                handleSettingChange({ cv_include_photo: checked })
              }}
            />
          }
        />
      </SettingsGroup>

      <SettingsGroup title={t('settings.groupAccount')}>
        <SettingsRow icon={Mail} title={t('emailChange.title')} subtitle={<span className="break-all">{user.email}</span>} onClick={() => setSheet('email')} testId="settings-email" />
        <SettingsRow icon={Globe} title={t('timezone.label')} subtitle={timeZone.replaceAll('_', ' ')} onClick={() => setSheet('timezone')} testId="settings-timezone" />
        <SettingsRow icon={Gauge} title={t('usage.title')} subtitle={t('settings.limitsSubtitle')} to="/settings/limits" testId="settings-limits" />
        <SettingsRow icon={Shield} title={t('account.privacyTitle')} subtitle={t('account.privacyHint')} to="/settings/privacy" testId="settings-privacy" />
      </SettingsGroup>

      <SettingsGroup title={t('settings.groupApp')}>
        <NotificationsRow enabled={notificationsEnabled} onPreferenceChange={handleNotificationsPreference} />
        <SettingsRow
          icon={Languages}
          title={t('account.interfaceLanguage')}
          subtitle={t(`settings.languageName_${lang}`)}
          onClick={() => setSheet('language')}
          testId="settings-language"
        />
      </SettingsGroup>

      <LogoutButton />

      <ChoiceSheet
        open={sheet === 'cvLanguage'}
        onOpenChange={(open) => setSheet(open ? 'cvLanguage' : null)}
        title={t('onboarding.cvLanguageLabel')}
        description={t('settings.cvLanguageHint')}
        name="cv-language"
        value={cvLanguageMode}
        options={cvLanguageOptions}
        onChange={(value) => {
          setCvLanguageMode(value)
          handleSettingChange({ cv_language_mode: value })
        }}
      />
      <ChoiceSheet
        open={sheet === 'language'}
        onOpenChange={(open) => setSheet(open ? 'language' : null)}
        title={t('account.interfaceLanguage')}
        name="interface-language"
        value={lang}
        options={interfaceOptions}
        onChange={(next) => {
          setLang(next)
          handleSettingChange({ interface_language: next })
        }}
      />
      <Sheet open={sheet === 'email'} onOpenChange={(open) => setSheet(open ? 'email' : null)}>
        <SheetContent>
          <SheetHeader title={t('emailChange.title')} />
          <SheetBody className="pt-3">
            <EmailChangeForm currentEmail={user.email} />
          </SheetBody>
        </SheetContent>
      </Sheet>
      <TimezoneSheet
        open={sheet === 'timezone'}
        onOpenChange={(open) => setSheet(open ? 'timezone' : null)}
        value={timeZone}
        onSave={async (next) => {
          setTimeZone(next)
          if (await handleSettingChange({ timezone: next })) setSheet(null)
        }}
      />
    </div>
  )
}

function TimezoneSheet({ open, onOpenChange, value, onSave }) {
  const { t } = useLanguage()
  const [draft, setDraft] = useState(value)
  useEffect(() => {
    if (open) setDraft(value)
  }, [open, value])
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader title={t('timezone.label')} description={t('timezone.hint')} />
        <SheetBody className="pt-3">
          <label htmlFor="account-timezone" className="text-[13px] font-semibold text-label">
            {t('timezone.label')}
          </label>
          <TimezoneSelect id="account-timezone" value={draft} onChange={setDraft} />
        </SheetBody>
        <SheetFooter>
          <Button size="lg" onClick={() => onSave(draft)}>
            {t('settings.save')}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
