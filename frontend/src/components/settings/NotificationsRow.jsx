import { useEffect, useState } from 'react'
import { Bell, Plus, Share } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import { fetchVapidPublicKey, registerPushSubscription } from '../../api/notifications'
import { isIOS, isPushSupported, isStandalone, subscribeToPush, unsubscribeFromPush } from '../../lib/push'
import { Button } from '@/components/ui/button'
import { Sheet, SheetBody, SheetClose, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { SettingsRow } from './SettingsList'

// Notifiche push nell'elenco Impostazioni (Sprint 78, mockup `impostazioni`,
// `notifications-ios`). Stessi due livelli di prima: l'interruttore è la
// preferenza dell'account (`notifications_enabled`, spenta = sottoscrizioni
// di tutti i dispositivi eliminate); sotto, lo stato di questo dispositivo
// con "Attiva notifiche". Su iPhone/iPad fuori dalla schermata Home le
// istruzioni (pannello "Come fare"): il controllo su iOS viene prima di quello
// sul supporto push, perché Safari fuori dalla Home non espone il push e
// prima mostrava "non supportate" invece delle istruzioni (difetto rilevato
// nello Sprint 73).
function IosSheet({ open, onOpenChange }) {
  const { t } = useLanguage()
  const steps = [
    [t('settings.iosStep1'), Share],
    [t('settings.iosStep2'), Plus],
    [t('settings.iosStep3'), Bell],
  ]
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader title={t('settings.iosSheetTitle')} description={t('settings.iosSheetIntro')} />
        <SheetBody className="pt-3">
          <ol className="flex flex-col divide-y divide-border rounded-card border border-border">
            {steps.map(([text, Icon], index) => (
              <li key={index} className="flex items-center gap-3.5 px-4 py-3.5">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-bold text-chip-foreground">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1 text-[15px] leading-snug text-foreground">{text}</span>
                <Icon className="h-5 w-5 shrink-0 text-chip-foreground" aria-hidden="true" />
              </li>
            ))}
          </ol>
        </SheetBody>
        <SheetFooter>
          <SheetClose asChild>
            <Button size="lg">{t('settings.gotIt')}</Button>
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}

export default function NotificationsRow({ enabled, onPreferenceChange }) {
  const { t } = useLanguage()
  const [status, setStatus] = useState('idle')
  const [iosOpen, setIosOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function check() {
      if (!isPushSupported() || !navigator.serviceWorker.controller) return
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (subscription && !cancelled) setStatus('granted')
    }
    check()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleToggle(next) {
    if (!next) {
      try {
        await unsubscribeFromPush()
      } catch {
        // la sottoscrizione lato server viene comunque eliminata
      }
      setStatus('idle')
    }
    onPreferenceChange(next)
  }

  async function handleEnable() {
    setStatus('requesting')
    try {
      const vapidPublicKey = await fetchVapidPublicKey()
      const result = await subscribeToPush(vapidPublicKey)
      if (result.status === 'granted' && result.subscription) {
        await registerPushSubscription(result.subscription)
        setStatus('granted')
      } else {
        setStatus(result.status)
      }
    } catch {
      setStatus('error')
    }
  }

  let device
  if (!enabled) {
    device = <p className="text-sm text-muted-foreground">{t('account.notificationsOffHint')}</p>
  } else if (isIOS() && !isStandalone()) {
    device = (
      <div className="flex flex-col items-start gap-1.5">
        <p className="text-sm text-muted-foreground">{t('account.notificationsIosHint')}</p>
        <Button variant="text" size="sm" className="-ml-3" onClick={() => setIosOpen(true)}>
          {t('settings.howTo')}
        </Button>
      </div>
    )
  } else if (!isPushSupported()) {
    device = <p className="text-sm text-muted-foreground">{t('account.notificationsUnsupported')}</p>
  } else if (status === 'granted') {
    device = <p className="text-sm font-semibold text-success">{t('account.notificationsEnabled')}</p>
  } else if (status === 'denied') {
    device = <p className="text-sm text-destructive-text">{t('account.notificationsDenied')}</p>
  } else if (status === 'error') {
    device = <p className="text-sm text-destructive-text">{t('account.notificationsError')}</p>
  } else {
    device = (
      <Button variant="secondary" size="sm" className="w-fit" disabled={status === 'requesting'} onClick={handleEnable}>
        {t('account.notificationsEnable')}
      </Button>
    )
  }

  return (
    <>
      <SettingsRow
        icon={Bell}
        title={t('account.notificationsTitle')}
        subtitle={t('settings.notificationsSubtitle')}
        testId="settings-notifications"
        trailing={
          <Switch checked={enabled} onCheckedChange={handleToggle} label={t('account.notificationsPreference')} />
        }
      >
        <div className="mt-2">{device}</div>
      </SettingsRow>
      <IosSheet open={iosOpen} onOpenChange={setIosOpen} />
    </>
  )
}
