import { useLanguage } from '../i18n/LanguageContext'
import { cn } from '../lib/utils'

// Avviso di trasparenza AI (Sprint 67): vicino a ogni punto in cui l'app
// genera testo con l'AI (chat degli editor, generazione di CV, cover letter
// e messaggi di networking).
export default function AiNotice({ className }) {
  const { t } = useLanguage()
  return <p className={cn('text-xs text-muted-foreground', className)}>{t('common.aiNotice')}</p>
}
