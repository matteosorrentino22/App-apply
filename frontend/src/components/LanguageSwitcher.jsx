import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { updateMe } from '../api/auth'
import { SUPPORTED_LANGUAGES } from '../i18n/translations'

export default function LanguageSwitcher() {
  const { lang, setLang } = useLanguage()
  const { user } = useAuth()

  function handleChange(event) {
    const next = event.target.value
    setLang(next)
    if (user) {
      updateMe({ interface_language: next }).catch(() => {})
    }
  }

  return (
    <select className="language-switcher" value={lang} onChange={handleChange} aria-label="Lingua / Language">
      {SUPPORTED_LANGUAGES.map((code) => (
        <option key={code} value={code}>
          {code.toUpperCase()}
        </option>
      ))}
    </select>
  )
}
