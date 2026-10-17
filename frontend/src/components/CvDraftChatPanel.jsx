import { useEffect, useRef, useState } from 'react'
import { Sparkles, X } from 'lucide-react'
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
      return { label: t('cvEditor.chatActionSummary'), before: content.summary, after: action.text }
    case 'update_qualification':
      return { label: t('cvEditor.chatActionQualification'), before: content.qualification, after: action.text }
    case 'update_role':
      return { label: t('cvEditor.chatActionRole').replace('{company}', company), before: exp?.role, after: action.text }
    case 'update_bullet':
      return {
        label: t('cvEditor.chatActionBullet').replace('{company}', company),
        before: exp?.bullets?.[action.bullet_index]?.text,
        after: action.text,
      }
    case 'add_bullet':
      return { label: t('cvEditor.chatActionNewBullet').replace('{company}', company), before: null, after: action.text }
    case 'hide_bullet':
      return {
        label: t('cvEditor.chatActionHideBullet').replace('{company}', company),
        before: exp?.bullets?.[action.bullet_index]?.text,
        after: null,
      }
    case 'show_bullet':
      return {
        label: t('cvEditor.chatActionShowBullet').replace('{company}', company),
        before: exp?.bullets?.[action.bullet_index]?.text,
        after: null,
      }
    case 'hide_experience':
      return { label: t('cvEditor.chatActionHideExperience').replace('{company}', company), before: null, after: null }
    case 'show_experience':
      return { label: t('cvEditor.chatActionShowExperience').replace('{company}', company), before: null, after: null }
    case 'update_area':
      return { label: t('cvEditor.chatActionArea'), before: content.areas_of_expertise[action.area_index], after: action.text }
    case 'add_area':
      return { label: t('cvEditor.chatActionNewArea'), before: null, after: action.text }
    case 'remove_area':
      return { label: t('cvEditor.chatActionRemoveArea'), before: content.areas_of_expertise[action.area_index], after: null }
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

function ActionCard({ action, content, t, decision, onDecide }) {
  const { label, before, after } = describeAction(action, content, t)
  return (
    <div
      className={cn(
        'rounded-lg border p-3 text-xs shadow-sm transition-opacity',
        decision ? 'border-border bg-muted/40 opacity-70' : 'border-border bg-background',
      )}
    >
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      {before ? (
        <p className="mb-1 rounded bg-destructive-soft px-2 py-1 text-destructive line-through">{before}</p>
      ) : null}
      {after ? <p className="rounded bg-success-soft px-2 py-1 text-success">{after}</p> : null}
      {decision ? (
        <p className="mt-2 text-xs font-medium text-muted-foreground">
          {decision === 'accepted' ? `✓ ${t('cvEditor.chatAccepted')}` : `✕ ${t('cvEditor.chatRejected')}`}
        </p>
      ) : (
        <div className="mt-2.5 flex gap-2">
          <Button type="button" size="sm" variant="primary" onClick={() => onDecide('accepted')}>
            {t('cvEditor.chatAccept')}
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => onDecide('rejected')}>
            {t('cvEditor.chatReject')}
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
        setError(t('cvEditor.chatErrorCredit'))
      } else {
        setError(t('cvEditor.chatErrorGeneric'))
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
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="flex h-full w-full max-w-sm flex-col bg-card shadow-2xl sm:rounded-l-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-2 border-b border-border p-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" />
            </span>
            <h2 className="text-sm font-semibold text-foreground">{t('cvEditor.chatTitle')}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('cvEditor.chatClose')}
            className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
          {history.length === 0 ? (
            <p className="text-xs text-muted-foreground">{t('cvEditor.chatEmpty')}</p>
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

        <div className="flex items-end gap-2 border-t border-border bg-muted/30 p-3">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                handleSend()
              }
            }}
            placeholder={t('cvEditor.chatPlaceholder')}
            className="min-h-10 flex-1 resize-none"
          />
          <Button type="button" disabled={sending || !input.trim()} onClick={handleSend}>
            {sending ? t('cvEditor.chatSending') : t('cvEditor.chatSend')}
          </Button>
        </div>
      </div>
    </div>
  )
}
