import { useEffect } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { LanguageProvider, useLanguage } from './i18n/LanguageContext'
import ProtectedRoute from './components/ProtectedRoute'
import LanguageSwitcher from './components/LanguageSwitcher'
import { ToastProvider } from './components/ToastProvider'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import OnboardingPage from './pages/onboarding/OnboardingPage'
import JobListPage from './pages/JobListPage'
import JobDetailPage from './pages/JobDetailPage'
import AccountPage from './pages/AccountPage'

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

function Topbar() {
  const { user } = useAuth()
  const { t } = useLanguage()

  return (
    <div className="mx-auto flex max-w-2xl items-center justify-end gap-4 px-4 pt-4">
      {user && (
        <Link to="/account" className="text-sm font-medium text-primary hover:underline">
          {t('account.navLink')}
        </Link>
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
                path="/account"
                element={
                  <ProtectedRoute>
                    <AccountPage />
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
