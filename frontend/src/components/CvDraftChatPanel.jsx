import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import { fetchCvDraftChat, sendCvDraftChatMessage } from '../api/jobs'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

function findExperience(content, profileExperienceId) {
  return content.experiences.find((exp) => exp.profile_experience_id === profileExperienceId)
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

  switch (action.type) {
    case 'update_summary':
      return { label: t('cvEditor.chat.actionSummary'), before: content.summary, after: action.text }
    case 'update_qualification':
      return { label: t('cvEditor.chat.actionQualification'), before: content.qualification, after: action.text }
    case 'update_role':
      return { label: t('cvEditor.chat.actionRole').replace('{company}', company), before: exp?.role, after: action.text }
    case 'update_bullet':
      return {
        label: t('cvEditor.chat.actionBullet').replace('{company}', company),
        before: exp?.bullets?.[action.bullet_index]?.text,
        after: action.text,
      }
    case 'add_bullet':
      return { label: t('cvEditor.chat.actionNewBullet').replace('{company}', company), before: null, after: action.text }
    case 'hide_bullet':
      return {
        label: t('cvEditor.chat.actionHideBullet').replace('{company}', company),
        before: exp?.bullets?.[action.bullet_index]?.text,
        after: null,
      }
    case 'show_bullet':
      return {
        label: t('cvEditor.chat.actionShowBullet').replace('{company}', company),
        before: exp?.bullets?.[action.bullet_index]?.text,
        after: null,
      }
    case 'hide_experience':
      return { label: t('cvEditor.chat.actionHideExperience').replace('{company}', company), before: null, after: null }
    case 'show_experience':
      return { label: t('cvEditor.chat.actionShowExperience').replace('{company}', company), before: null, after: null }
    case 'update_area':
      return { label: t('cvEditor.chat.actionArea'), before: content.areas_of_expertise[action.area_index], after: action.text }
    case 'add_area':
      return { label: t('cvEditor.chat.actionNewArea'), before: null, after: action.text }
    case 'remove_area':
      return { label: t('cvEditor.chat.actionRemoveArea'), before: content.areas_of_expertise[action.area_index], after: null }
    case 'toggle_skill':
      return { label: t('cvEditor.chat.actionSkill').replace('{name}', action.name), before: null, after: null }
    case 'toggle_certification':
      return { label: t('cvEditor.chat.actionCertification').replace('{name}', action.name), before: null, after: null }
    case 'update_education_notes':
      return {
        label: t('cvEditor.chat.actionEducationNotes').replace('{institution}', edu?.institution || ''),
        before: edu?.notes,
        after: action.text,
      }
    case 'update_language_level':
      return {
        label: t('cvEditor.chat.actionLanguageLevel').replace('{language}', language?.language || ''),
        before: language?.level,
        after: action.level,
      }
    default:
      return { label: action.type, before: null, after: null }
  }
}

function ActionCard({ action, content, t, decision, onDecide }) {
  const { label, before, after } = describeAction(action, content, t)
  return (
    <div className="rounded-md border border-border bg-background p-2.5 text-xs">
      <p className="mb-1 font-medium text-foreground">{label}</p>
      {before ? <p className="text-muted-foreground line-through">{before}</p> : null}
      {after ? <p className="text-foreground">{after}</p> : null}
      {decision ? (
        <p className="mt-1.5 font-medium text-muted-foreground">
          {decision === 'accepted' ? t('cvEditor.chat.accepted') : t('cvEditor.chat.rejected')}
        </p>
      ) : (
        <div className="mt-1.5 flex gap-2">
          <Button type="button" size="sm" variant="secondary" onClick={() => onDecide('accepted')}>
            {t('cvEditor.chat.accept')}
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => onDecide('rejected')}>
            {t('cvEditor.chat.reject')}
          </Button>
        </div>
      )}
    </div>
  )
}

export default function CvDraftChatPanel({ jobId, content, onApplyAction, onClose }) {
  const { t } = useLanguage()
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  // Clé = "<indice messaggio>-<indice azione>" → 'accepted' | 'rejected'
  // (Sprint 59): solo in memoria, non persistita — alla ricarica della
  // pagina le card tornano in attesa di decisione, scelta deliberata per
  // non aggiungere un giro di rete solo per questo stato ausiliario.
  const [decisions, setDecisions] = useState({})
  const scrollRef = useRef(null)

  useEffect(() => {
    fetchCvDraftChat(jobId)
      .then((data) => setHistory(data.history || []))
      .catch(() => {})
  }, [jobId])

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [history])

  async function handleSend() {
    const message = input.trim()
    if (!message || sending) return
    setSending(true)
    setError('')
    try {
      const { reply, actions } = await sendCvDraftChatMessage(jobId, message)
      setHistory((current) => [
        ...current,
        { role: 'user', message },
        { role: 'assistant', message: reply, actions },
      ])
      setInput('')
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setError(t('cvEditor.chat.errorCredit'))
      } else {
        setError(t('cvEditor.chat.errorGeneric'))
      }
    } finally {
      setSending(false)
    }
  }

  function handleDecide(messageIndex, actionIndex, action, decision) {
    setDecisions((current) => ({ ...current, [`${messageIndex}-${actionIndex}`]: decision }))
    if (decision === 'accepted') onApplyAction(action)
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/20 sm:bg-transparent">
      <div className="flex h-full w-full max-w-sm flex-col border-l border-border bg-card shadow-xl">
        <div className="flex items-center justify-between border-b border-border p-4">
          <h2 className="text-sm font-semibold text-foreground">{t('cvEditor.chat.title')}</h2>
          <button type="button" onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
          {history.length === 0 ? (
            <p className="text-xs text-muted-foreground">{t('cvEditor.chat.empty')}</p>
          ) : (
            <div className="flex flex-col gap-3">
              {history.map((turn, messageIndex) => (
                <div
                  key={messageIndex}
                  className={cn('flex flex-col gap-2', turn.role === 'user' ? 'items-end' : 'items-start')}
                >
                  <div
                    className={cn(
                      'max-w-[90%] rounded-lg px-3 py-2 text-sm',
                      turn.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground',
                    )}
                  >
                    {turn.message}
                  </div>
                  {turn.actions?.length > 0 && (
                    <div className="flex w-[90%] flex-col gap-2">
                      {turn.actions.map((action, actionIndex) => (
                        <ActionCard
                          key={actionIndex}
                          action={action}
                          content={content}
                          t={t}
                          decision={decisions[`${messageIndex}-${actionIndex}`]}
                          onDecide={(decision) => handleDecide(messageIndex, actionIndex, action, decision)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {error && <p className="px-4 text-xs text-destructive">{error}</p>}

        <div className="flex items-end gap-2 border-t border-border p-3">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                handleSend()
              }
            }}
            placeholder={t('cvEditor.chat.placeholder')}
            className="min-h-10 flex-1 resize-none"
          />
          <Button type="button" disabled={sending || !input.trim()} onClick={handleSend}>
            {sending ? t('cvEditor.chat.sending') : t('cvEditor.chat.send')}
          </Button>
        </div>
      </div>
    </div>
  )
}
