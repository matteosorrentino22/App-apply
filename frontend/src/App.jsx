import { useEffect } from 'react'
import { BrowserRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { LanguageProvider, useLanguage } from './i18n/LanguageContext'
import ProtectedRoute from './components/ProtectedRoute'
import LanguageSwitcher from './components/LanguageSwitcher'
import { ToastProvider } from './components/ToastProvider'
import { buttonVariants } from './components/ui/button'
import { cn } from './lib/utils'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import OnboardingPage from './pages/onboarding/OnboardingPage'
import HomePage from './pages/HomePage'
import JobListPage from './pages/JobListPage'
import JobDetailPage from './pages/JobDetailPage'
import AccountPage from './pages/AccountPage'
import ProfilePage from './pages/ProfilePage'

// Una volta caricato l'account, la sua preferenza salvata (interface_language)
// prevale sul rilevamento da dispositivo usato come default iniziale.
function AccountLanguageSync() {
  const { user } = useAuth()
  const { lang, setLang } = useLanguage()

  useEffect(() => {
    if (user?.interface_language && user.interface_language !== lang) {
      setLang(user.interface_language)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  return null
}

function NavItem({ to, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          buttonVariants({ variant: isActive ? 'primary' : 'ghost', size: 'sm' }),
          'rounded-full px-4',
        )
      }
    >
      {label}
    </NavLink>
  )
}

function Topbar() {
  const { user } = useAuth()
  const { t } = useLanguage()

  return (
    <div
      className={cn(
        'mx-auto flex max-w-2xl items-center gap-4 px-4 pt-4',
        user ? 'justify-between' : 'justify-end',
      )}
    >
      {user && (
        <nav className="flex items-center gap-1 rounded-full bg-muted p-1">
          <NavItem to="/home" label={t('home.navLink')} />
          <NavItem to="/list" label={t('jobs.navLink')} />
          <NavItem to="/profile" label={t('profile.navLink')} />
          <NavItem to="/settings" label={t('account.navLink')} />
        </nav>
      )}
      <LanguageSwitcher />
    </div>
  )
}

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ToastProvider>
          <AccountLanguageSync />
          <BrowserRouter>
            <Topbar />
            <Routes>
              <Route path="/" element={<Navigate to="/list" replace />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/onboarding"
                element={
                  <ProtectedRoute>
                    <OnboardingPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/home"
                element={
                  <ProtectedRoute>
                    <HomePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/list"
                element={
                  <ProtectedRoute>
                    <JobListPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/jobs/:id"
                element={
                  <ProtectedRoute>
                    <JobDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <AccountPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </LanguageProvider>
  )
}
