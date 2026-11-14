import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { LanguageProvider, useLanguage } from './i18n/LanguageContext'
import ProtectedRoute from './components/ProtectedRoute'
import { ToastProvider } from './components/ToastProvider'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import OnboardingPage from './pages/onboarding/OnboardingPage'
import JobListPage from './pages/JobListPage'
import JobDetailPage from './pages/JobDetailPage'
import CvDraftEditorPage from './pages/CvDraftEditorPage'
import CoverLetterDraftEditorPage from './pages/CoverLetterDraftEditorPage'
import AccountPage from './pages/AccountPage'
import ProfilePage from './pages/ProfilePage'
import LegalPage from './pages/LegalPage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import ConfirmEmailChangePage from './pages/ConfirmEmailChangePage'
import AppShell from './components/AppShell'
import AppUpdateBanner from './components/AppUpdateBanner'
import ProfileCompletionBanner from './components/ProfileCompletionBanner'

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

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ToastProvider>
          <AccountLanguageSync />
          <BrowserRouter>
            <AppShell banner={<ProfileCompletionBanner />}>
              <Routes>
                <Route path="/" element={<Navigate to="/list" replace />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/privacy" element={<LegalPage document="privacy" />} />
                <Route path="/terms" element={<LegalPage document="terms" />} />
                <Route path="/verify-email" element={<VerifyEmailPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/confirm-email-change" element={<ConfirmEmailChangePage />} />
                <Route
                  path="/onboarding"
                  element={
                    <ProtectedRoute>
                      <OnboardingPage />
                    </ProtectedRoute>
                  }
                />
                {/* Home eliminata (Sprint 73, SPEC-DELTA A1): statistiche e raccolta sono in Jobs. */}
                <Route path="/home" element={<Navigate to="/list" replace />} />
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
                  path="/jobs/:id/cv-editor"
                  element={
                    <ProtectedRoute>
                      <CvDraftEditorPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/jobs/:id/cover-letter-editor"
                  element={
                    <ProtectedRoute>
                      <CoverLetterDraftEditorPage />
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
            </AppShell>
            <AppUpdateBanner />
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </LanguageProvider>
  )
}
