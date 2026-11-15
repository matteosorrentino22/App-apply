import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth'
import { ApiError, AUTH_EXPIRED_EVENT, LEGAL_REQUIRED_EVENT } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  // Sprint 80: il primo /me non è riuscito per rete o server (non 401/403).
  // Il token resta: ProtectedRoute mostra "Connessione non riuscita" con
  // "Riprova" invece di mandare al login chi ha una sessione valida.
  const [connectionError, setConnectionError] = useState(false)

  const refreshUser = useCallback(async () => {
    try {
      const me = await authApi.fetchMe()
      setUser(me)
      setConnectionError(false)
      return me
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setUser(null)
        setConnectionError(false)
        return null
      }
      throw error
    }
  }, [])

  useEffect(() => {
    refreshUser()
      .catch(() => setConnectionError(true))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const handleExpired = () => setUser(null)
    const handleLegalRequired = () => {
      refreshUser().catch(() => {})
    }
    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired)
    window.addEventListener(LEGAL_REQUIRED_EVENT, handleLegalRequired)
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired)
      window.removeEventListener(LEGAL_REQUIRED_EVENT, handleLegalRequired)
    }
  }, [refreshUser])

  const login = useCallback(async (email, password) => {
    await authApi.login(email, password)
    return refreshUser()
  }, [refreshUser])

  // Restituisce la risposta della registrazione: con `verification_required`
  // non c'è ancora un token e l'utente resta fuori finché non conferma l'email.
  const register = useCallback(async (payload) => {
    const data = await authApi.register(payload)
    if (data.token) await refreshUser()
    return data
  }, [refreshUser])

  const retryConnection = useCallback(async () => {
    setLoading(true)
    try {
      await refreshUser()
    } catch {
      setConnectionError(true)
    } finally {
      setLoading(false)
    }
  }, [refreshUser])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, connectionError, retryConnection, login, register, logout, refreshUser, setUser }),
    [user, loading, connectionError, retryConnection, login, register, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth va usato dentro <AuthProvider>')
  }
  return context
}
