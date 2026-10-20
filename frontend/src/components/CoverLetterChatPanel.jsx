import { useEffect, useRef, useState } from 'react'
import { Sparkles, X } from 'lucide-react'
import {
  fetchCoverLetterDraftChat,
  recordCoverLetterChatDecision,
  sendCoverLetterDraftChatMessage,
} from '../api/jobs'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

// Mirror semplificato di CvDraftChatPanel.jsx (Sprint 63): solo 3 tipi di
// azione (nessuna skill/certification/esperienza da gestire), nessun
// pulsante di "puntamento" di un singolo paragrafo come contesto — con
// 3-5 paragrafi in tutto il solo riferimento testuale nel messaggio è
// già sufficientemente chiaro, a differenza dei bullet del CV.
function describeAction(action, content, t) {
  switch (action.type) {
    case 'update_paragraph':
      return {
        label: t('coverLetterEditor.chatActionUpdate'),
        before: content.paragraphs[action.paragraph_index],
        after: action.text,
      }
    case 'add_paragraph':
      return { label: t('coverLetterEditor.chatActionAdd'), before: null, after: action.text }
    case 'remove_paragraph':
      return {
        label: t('coverLetterEditor.chatActionRemove'),
        before: content.paragraphs[action.paragraph_index],
        after: null,
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

export default function CoverLetterChatPanel({ open, jobId, content, onApplyAction, onClose }) {
  const { t } = useLanguage()
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [decisions, setDecisions] = useState({})
  const scrollRef = useRef(null)

  useEffect(() => {
    fetchCoverLetterDraftChat(jobId)
      .then((data) => {
        const loadedHistory = data.history || []
        setHistory(loadedHistory)
        const loadedDecisions = {}
        loadedHistory.forEach((turn, messageIndex) => {
          const actions = turn.actions || []
          actions.forEach((action, actionIndex) => {
            if (action.decision) loadedDecisions[`${messageIndex}-${actionIndex}`] = action.decision
          })
        })
        setDecisions(loadedDecisions)
      })
      .catch(() => {})
  }, [jobId])

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [history])

  if (!open) return null

  async function handleSend() {
    const message = input.trim()
    if (!message || sending) return
    setSending(true)
    setError('')
    try {
      const { reply, actions } = await sendCoverLetterDraftChatMessage(jobId, message)
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
    recordCoverLetterChatDecision(jobId, messageIndex, actionIndex, decision).catch(() => {})
  }

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-sm flex-col bg-card shadow-2xl sm:rounded-l-2xl">
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
  )
}
