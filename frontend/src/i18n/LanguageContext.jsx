import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { translations } from './translations'
import { currentLanguage, LANG_STORAGE_KEY, SUPPORTED_LANGUAGES } from './language'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(currentLanguage)

  const setLang = useCallback((next) => {
    if (!SUPPORTED_LANGUAGES.includes(next)) return
    setLangState(next)
    localStorage.setItem(LANG_STORAGE_KEY, next)
  }, [])

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const t = useCallback(
    (path) => {
      const keys = path.split('.')
      let node = translations[lang]
      for (const key of keys) {
        node = node?.[key]
      }
      return node ?? path
    },
    [lang],
  )

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage va usato dentro <LanguageProvider>')
  }
  return context
}
