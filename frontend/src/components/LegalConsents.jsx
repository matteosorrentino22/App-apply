import { Link } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import { Checkbox } from '@/components/ui/checkbox'

// Le tre spunte obbligatorie (Sprint 67), mai pre-selezionate: registrazione
// e schermata di accettazione per gli utenti esistenti. I link aprono le
// pagine legali in una nuova scheda per non perdere il modulo compilato.
export default function LegalConsents({ consents, onChange, idPrefix = 'consent' }) {
  const { t } = useLanguage()
  const set = (key) => (checked) => onChange({ ...consents, [key]: checked === true })
  const linkClass = 'font-medium text-primary underline'

  return (
    <div className="flex flex-col gap-3">
      <label htmlFor={`${idPrefix}-privacy`} className="flex items-start gap-2.5 text-sm">
        <Checkbox id={`${idPrefix}-privacy`} className="mt-0.5" checked={consents.privacy} onCheckedChange={set('privacy')} />
        <span>
          {t('register.acceptPrivacyBefore')}
          <Link to="/privacy" target="_blank" rel="noopener" className={linkClass}>
            {t('register.acceptPrivacyLink')}
          </Link>
          {t('register.acceptPrivacyAfter')}
        </span>
      </label>
      <label htmlFor={`${idPrefix}-terms`} className="flex items-start gap-2.5 text-sm">
        <Checkbox id={`${idPrefix}-terms`} className="mt-0.5" checked={consents.terms} onCheckedChange={set('terms')} />
        <span>
          {t('register.acceptTermsBefore')}
          <Link to="/terms" target="_blank" rel="noopener" className={linkClass}>
            {t('register.acceptTermsLink')}
          </Link>
          {t('register.acceptTermsAfter')}
        </span>
      </label>
      <label htmlFor={`${idPrefix}-age`} className="flex items-start gap-2.5 text-sm">
        <Checkbox id={`${idPrefix}-age`} className="mt-0.5" checked={consents.age} onCheckedChange={set('age')} />
        <span>{t('register.confirmAge')}</span>
      </label>
    </div>
  )
}
