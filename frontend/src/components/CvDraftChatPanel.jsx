import { useLanguage } from '../i18n/LanguageContext'
import DraftChatPanel from './DraftChatPanel'

function findExperience(content, profileExperienceId) {
  return content.experiences.find((exp) => exp.profile_experience_id === profileExperienceId)
}

// Bullet per id stabile (Sprint 69), non per posizione.
function findBullet(exp, bulletId) {
  return exp?.bullets?.find((bullet) => bullet.id === bulletId)
}

function truncate(text, maxLength) {
  if (!text) return ''
  return text.length > maxLength ? `${text.slice(0, maxLength).trim()}…` : text
}

// Etichetta leggibile di una singola azione proposta (Sprint 59): usata sia
// per il titolo della card sia per il "prima" mostrato all'utente — nessuna
// chiamata di rete, solo lettura dello stato attuale della bozza (`content`,
// la stessa fonte di verità già usata dal resto dell'editor).
function describeAction(action, content, t) {
  const exp =
    action.profile_experience_id != null ? findExperience(content, action.profile_experience_id) : null
  const company = exp?.company || ''
  const edu = action.education_index != null ? content.educations[action.education_index] : null
  const language = action.language_index != null ? content.languages[action.language_index] : null
  const bullet = findBullet(exp, action.bullet_id)
  const areaBefore = action.area_text ?? content.areas_of_expertise[action.area_index]

  switch (action.type) {
    case 'update_summary':
      return { label: t('cvEditor.chatActionSummary'), before: content.summary, after: action.text }
    case 'update_qualification':
      return { label: t('cvEditor.chatActionQualification'), before: content.qualification, after: action.text }
    case 'update_role':
      return { label: t('cvEditor.chatActionRole').replace('{company}', company), before: exp?.role, after: action.text }
    case 'update_bullet':
      return {
        label: t('cvEditor.chatActionBullet').replace('{company}', company),
        before: bullet?.text,
        after: action.text,
      }
    case 'add_bullet':
      return { label: t('cvEditor.chatActionNewBullet').replace('{company}', company), before: null, after: action.text }
    case 'hide_bullet':
      return {
        label: t('cvEditor.chatActionHideBullet').replace('{company}', company),
        before: bullet?.text,
        after: null,
      }
    case 'show_bullet':
      return {
        label: t('cvEditor.chatActionShowBullet').replace('{company}', company),
        before: bullet?.text,
        after: null,
      }
    case 'hide_experience':
      return { label: t('cvEditor.chatActionHideExperience').replace('{company}', company), before: null, after: null }
    case 'show_experience':
      return { label: t('cvEditor.chatActionShowExperience').replace('{company}', company), before: null, after: null }
    case 'update_area':
      return { label: t('cvEditor.chatActionArea'), before: areaBefore, after: action.text }
    case 'add_area':
      return { label: t('cvEditor.chatActionNewArea'), before: null, after: action.text }
    case 'remove_area':
      return { label: t('cvEditor.chatActionRemoveArea'), before: areaBefore, after: null }
    case 'toggle_skill':
      return { label: t('cvEditor.chatActionSkill').replace('{name}', action.name), before: null, after: null }
    case 'toggle_certification':
      return { label: t('cvEditor.chatActionCertification').replace('{name}', action.name), before: null, after: null }
    case 'update_education_notes':
      return {
        label: t('cvEditor.chatActionEducationNotes').replace('{institution}', edu?.institution || ''),
        before: edu?.notes,
        after: action.text,
      }
    case 'update_language_level':
      return {
        label: t('cvEditor.chatActionLanguageLevel').replace('{language}', language?.language || ''),
        before: language?.level,
        after: action.level,
      }
    default:
      return { label: action.type, before: null, after: null }
  }
}

// Chat dell'editor del CV (Sprint 59–62, 69; dallo Sprint 76 presentazione
// in DraftChatPanel e stato in `useDraftChat`, nella pagina). Qui restano le
// etichette delle proposte e il contesto dei bullet "puntati" (Sprint 61),
// che si tolgono anche dalla ✕ del chip.
export default function CvDraftChatPanel({ chat, content, focusedBullets, onToggleFocus, showHeader }) {
  const { t } = useLanguage()
  const context = (focusedBullets || [])
    .map(({ profileExperienceId, bulletId }) => ({
      key: bulletId,
      label: truncate(findBullet(findExperience(content, profileExperienceId), bulletId)?.text?.replace(/\*\*/g, ''), 40),
      onRemove: () => onToggleFocus(profileExperienceId, bulletId),
    }))
    .filter((item) => item.label)

  return (
    <DraftChatPanel
      chat={chat}
      describe={(action) => describeAction(action, content, t)}
      emptyText={t('cvEditor.chatEmpty')}
      placeholder={t('cvEditor.chatPlaceholder')}
      title={t('cvEditor.chatTitle')}
      showHeader={showHeader}
      context={context}
      onSend={() => chat.send(focusedBullets)}
    />
  )
}
