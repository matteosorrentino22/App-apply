import { Link } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'

// Footer discreto con i link alle pagine legali (Sprint 67), su tutte le pagine.
export default function LegalFooter() {
  const { t } = useLanguage()
  return (
    <footer className="mx-auto flex max-w-2xl items-center justify-center gap-3 px-4 pb-3 text-xs text-muted-foreground">
      <Link to="/privacy" className="inline-flex min-h-11 items-center px-1 hover:text-foreground hover:underline">
        {t('legal.privacy')}
      </Link>
      <span aria-hidden="true">·</span>
      <Link to="/terms" className="inline-flex min-h-11 items-center px-1 hover:text-foreground hover:underline">
        {t('legal.terms')}
      </Link>
    </footer>
  )
}
