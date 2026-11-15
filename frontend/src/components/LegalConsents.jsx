import { Link } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import { Checkbox } from '@/components/ui/checkbox'

// Le tre spunte obbligatorie (Sprint 67), mai pre-selezionate: registrazione
// e schermata di accettazione per gli utenti esistenti. I link aprono le
// pagine legali in una nuova scheda per non perdere il modulo compilato.
export default function LegalConsents({ consents, onChange, idPrefix = 'consent' }) {
  const { t } = useLanguage()
  const set = (key) => (checked) => onChange({ ...consents, [key]: checked === true })
  const linkClass = 'font-bold text-primary underline'
  // Sprint 79: solo aspetto (casella da 24 px, testo da 15 px, righe più alte).
  const rowClass = 'flex min-h-11 cursor-pointer items-start gap-3 py-1 text-[15px] leading-snug text-foreground'

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={`${idPrefix}-privacy`} className={rowClass}>
        <Checkbox id={`${idPrefix}-privacy`} className="shrink-0" checked={consents.privacy} onCheckedChange={set('privacy')} />
        <span>
          {t('register.acceptPrivacyBefore')}
          <Link to="/privacy" target="_blank" rel="noopener" className={linkClass}>
            {t('register.acceptPrivacyLink')}
          </Link>
          {t('register.acceptPrivacyAfter')}
        </span>
      </label>
      <label htmlFor={`${idPrefix}-terms`} className={rowClass}>
        <Checkbox id={`${idPrefix}-terms`} className="shrink-0" checked={consents.terms} onCheckedChange={set('terms')} />
        <span>
          {t('register.acceptTermsBefore')}
          <Link to="/terms" target="_blank" rel="noopener" className={linkClass}>
            {t('register.acceptTermsLink')}
          </Link>
          {t('register.acceptTermsAfter')}
        </span>
      </label>
      <label htmlFor={`${idPrefix}-age`} className={rowClass}>
        <Checkbox id={`${idPrefix}-age`} className="shrink-0" checked={consents.age} onCheckedChange={set('age')} />
        <span>{t('register.confirmAge')}</span>
      </label>
    </div>
  )
}
