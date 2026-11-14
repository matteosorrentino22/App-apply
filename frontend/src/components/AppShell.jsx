import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Briefcase, Settings, UserRound } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import BrandLogo from './BrandLogo'
import LanguageSwitcher from './LanguageSwitcher'
import LegalFooter from './LegalFooter'
import { cn } from '@/lib/utils'

// Navigazione a 3 voci (Sprint 73, Docs/design/DESIGN.md §2, SPEC-DELTA A1).
// Jobs è attiva anche sul dettaglio e sugli editor di un job.
const NAV_ITEMS = [
  { to: '/list', labelKey: 'jobs.navLink', icon: Briefcase, match: ['/list', '/jobs'] },
  { to: '/profile', labelKey: 'profile.navLink', icon: UserRound, match: ['/profile'] },
  { to: '/settings', labelKey: 'account.navLink', icon: Settings, match: ['/settings'] },
]

function useActiveItem() {
  const { pathname } = useLocation()
  return NAV_ITEMS.find((item) => item.match.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)))
}

// Da 1024 px: barra in alto a tutta larghezza (mockup `desk-jobs`) con logo,
// voci a pillola (attiva su --primary-soft) e lingua. Niente "Esci": sta in
// Impostazioni (A9).
function DesktopTopBar() {
  const { t } = useLanguage()
  const active = useActiveItem()
  return (
    <header className="sticky top-0 z-30 hidden border-b border-border bg-card pt-[env(safe-area-inset-top)] lg:block">
      <div className="flex h-16 items-center justify-between gap-6 px-8">
        <div className="flex items-center gap-10">
          <Link to="/list" aria-label={t('nav.homeLink')} className="rounded-field outline-none focus-visible:ring-3 focus-visible:ring-ring/30">
            <BrandLogo />
          </Link>
          <nav aria-label={t('nav.main')} className="flex gap-1">
            {NAV_ITEMS.map((item) => {
              const isActive = active === item
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'flex min-h-10 items-center rounded-[10px] px-3.5 text-[15px] outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/30',
                    isActive ? 'bg-primary-soft font-bold text-primary' : 'font-semibold text-muted-foreground hover:text-foreground',
                  )}
                >
                  {t(item.labelKey)}
                </Link>
              )
            })}
          </nav>
        </div>
        <LanguageSwitcher compact />
      </div>
    </header>
  )
}

// Sotto i 1024 px: barra di tab in basso (mockup `jobs-lista`), icona +
// etichetta, voce attiva in colore primario, area sicura dell'iPhone.
// Nascosta dove c'è la barra azione (dettaglio job, Sprint 75: classe
// `has-actionbar` su <html>, index.css).
function BottomTabBar() {
  const { t } = useLanguage()
  const active = useActiveItem()
  return (
    <nav
      aria-label={t('nav.main')}
      className="app-tabbar fixed inset-x-0 bottom-0 z-30 flex justify-around border-t border-border bg-card px-[max(16px,env(safe-area-inset-left))] pt-2 pb-[max(8px,env(safe-area-inset-bottom))] lg:hidden"
    >
      {NAV_ITEMS.map((item) => {
        const isActive = active === item
        const Icon = item.icon
        return (
          <Link
            key={item.to}
            to={item.to}
            aria-current={isActive ? 'page' : undefined}
            className={cn(
              'flex min-h-12 min-w-[88px] flex-col items-center justify-center gap-[3px] rounded-field px-1 text-xs outline-none focus-visible:ring-3 focus-visible:ring-ring/30',
              isActive ? 'font-bold text-primary' : 'font-semibold text-muted-foreground',
            )}
          >
            <Icon className="h-[22px] w-[22px]" strokeWidth={isActive ? 2.2 : 2} aria-hidden="true" />
            <span className="text-center leading-tight">{t(item.labelKey)}</span>
          </Link>
        )
      })}
    </nav>
  )
}

// Pagine senza navigazione (accesso, legali, verifica email, schermata di
// accettazione): logo e selettore lingua, come nel mockup `login`.
function PublicHeader() {
  return (
    <header className="pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-2xl items-center justify-between gap-4 px-4 pt-5">
        <BrandLogo size={34} />
        <LanguageSwitcher compact />
      </div>
    </header>
  )
}

export default function AppShell({ children, banner }) {
  const { user } = useAuth()
  // Finché mancano le accettazioni legali (Sprint 67) ogni pagina protetta
  // mostra la schermata di accettazione: la navigazione non serve.
  const showNav = Boolean(user && !user.legal_acceptance_required)

  // `--app-bottom-bar` (index.css) tiene sopra la barra di tab gli elementi
  // fissi in basso (toast, nuova versione, pulsante chat degli editor).
  useEffect(() => {
    document.documentElement.classList.toggle('has-tabbar', showNav)
    return () => document.documentElement.classList.remove('has-tabbar')
  }, [showNav])

  return (
    // Su mobile le pagine autenticate non hanno testata: il padding in alto
    // tiene il contenuto sotto la status bar dell'iPhone (viewport-fit=cover).
    <div
      className={cn(
        'flex min-h-dvh flex-col pb-[var(--app-bottom-bar)]',
        showNav && 'pt-[env(safe-area-inset-top)] lg:pt-0',
      )}
    >
      {showNav ? <DesktopTopBar /> : <PublicHeader />}
      {/* Avvisi di sistema (nuova versione, profilo incompleto): in cima alla
          colonna, anche nelle pagine senza navigazione (la nuova versione). */}
      <div className="mx-auto w-full max-w-2xl px-4 pt-4 empty:hidden">{banner}</div>
      <main className="flex-1">{children}</main>
      <LegalFooter />
      {showNav ? <BottomTabBar /> : null}
    </div>
  )
}
