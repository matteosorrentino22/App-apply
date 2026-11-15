import { useLanguage } from '../i18n/LanguageContext'
import DraftChatPanel from './DraftChatPanel'

// Mirror semplificato di CvDraftChatPanel.jsx (Sprint 63): solo 3 tipi di
// azione (nessuna skill/certification/esperienza da gestire), nessun
// pulsante di "puntamento" di un singolo paragrafo come contesto — con
// 3-5 paragrafi in tutto il solo riferimento testuale nel messaggio è
// già sufficientemente chiaro, a differenza dei bullet del CV. Dallo
// Sprint 69 i paragrafi sono `{id, text}` e le azioni usano `paragraph_id`;
// i testi del pannello sono quelli della cover letter, non del CV. Dallo
// Sprint 76 presentazione in DraftChatPanel e stato in `useDraftChat`.
function describeAction(action, content, t) {
  const paragraph = content.paragraphs.find((p) => p.id === action.paragraph_id)
  switch (action.type) {
    case 'update_paragraph':
      return {
        label: t('coverLetterEditor.chatActionUpdate'),
        before: paragraph?.text,
        after: action.text,
      }
    case 'add_paragraph':
      return { label: t('coverLetterEditor.chatActionAdd'), before: null, after: action.text }
    case 'remove_paragraph':
      return {
        label: t('coverLetterEditor.chatActionRemove'),
        before: paragraph?.text,
        after: null,
      }
    default:
      return { label: action.type, before: null, after: null }
  }
}

export default function CoverLetterChatPanel({ chat, content, showHeader }) {
  const { t } = useLanguage()
  return (
    <DraftChatPanel
      chat={chat}
      describe={(action) => describeAction(action, content, t)}
      emptyText={t('coverLetterEditor.chatEmpty')}
      placeholder={t('coverLetterEditor.chatPlaceholder')}
      title={t('coverLetterEditor.chatTitle')}
      showHeader={showHeader}
      onSend={() => chat.send()}
    />
  )
}
