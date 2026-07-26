import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { updateMe } from '../api/auth'
import { SUPPORTED_LANGUAGES } from '../i18n/translations'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export default function LanguageSwitcher() {
  const { lang, setLang } = useLanguage()
  const { user } = useAuth()

  function handleChange(next) {
    setLang(next)
    if (user) {
      updateMe({ interface_language: next }).catch(() => {})
    }
  }

  return (
    <Select value={lang} onValueChange={handleChange}>
      <SelectTrigger aria-label="Lingua / Language" className="w-20">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {SUPPORTED_LANGUAGES.map((code) => (
          <SelectItem key={code} value={code}>
            {code.toUpperCase()}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
