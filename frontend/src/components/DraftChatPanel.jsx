import { useEffect, useRef } from 'react'
import { ArrowUp, Info, Minus, Sparkles, X } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import AiNotice from '@/components/AiNotice'
import { Badge } from '@/components/ui/badge'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { MAX_CHAT_MESSAGE_LENGTH } from '../utils/draftLimits'
import { formatEuro } from '../utils/retry'

// Pannello della chat degli editor (Sprint 76, mockup `cv-assistant`,
// `cv-assistant-warn`, `cv-assistant-credit`, `desk-editor`): una sola
// implementazione per CV e cover letter, per la colonna desktop e per il
// pannello dal basso su mobile. Solo presentazione: lo stato è in
// `useDraftChat` (lib/useDraftChat.js). Proposta → Accetta / Rifiuta come
// prima; le proposte decise si chiudono con "Applicata" / "Rifiutata".

function ProposalCard({ action, describe, decision, onDecide }) {
  const { t } = useLanguage()
  const { label, before, after } = describe(action)
  if (decision) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-card border border-border bg-card px-4 py-3">
        <p className="min-w-0 break-words text-xs font-bold uppercase tracking-[0.08em] text-chip-foreground">{label}</p>
        <Badge variant={decision === 'accepted' ? 'success' : 'neutral'} className="shrink-0 text-xs">
          {decision === 'accepted' ? t('cvEditor.chatAccepted') : t('cvEditor.chatRejected')}
        </Badge>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3 rounded-card border border-input bg-card p-4">
      <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.08em] text-chip-foreground">
        <Sparkles className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="min-w-0 break-words">{label}</span>
      </p>
      {before ? (
        <p className={cn('break-words text-sm text-muted-foreground', after && 'line-through')}>{before}</p>
      ) : null}
      {after ? <p className="break-words rounded-field bg-secondary px-3 py-2.5 text-[15px] leading-normal text-foreground">{after}</p> : null}
      <div className="grid grid-cols-2 gap-2.5">
        <Button variant="secondary" onClick={() => onDecide('rejected')}>
          {t('cvEditor.chatReject')}
        </Button>
        <Button onClick={() => onDecide('accepted')}>{t('cvEditor.chatAccept')}</Button>
      </div>
    </div>
  )
}

function Notice({ notice }) {
  if (notice.variant === 'error') {
    return (
      <Banner variant="error" icon={Minus} className="w-[92%]">
        {notice.text}
      </Banner>
    )
  }
  return (
    <Banner variant="note" icon={Info} className="w-[92%]">
      {notice.text}
    </Banner>
  )
}

function PriceLine({ pricing }) {
  const { t, lang } = useLanguage()
  const [beforePrice, afterPrice] = t('cvEditor.chatPriceInfo').split('{price}')
  return (
    <p className="text-[13px] leading-snug text-muted-foreground">
      {beforePrice}
      <strong className="font-bold text-foreground">{formatEuro(pricing.price, lang)}</strong>
      {(afterPrice || '').replace('{balance}', formatEuro(pricing.balance, lang))}
    </p>
  )
}

export default function DraftChatPanel({
  chat,
  describe,
  emptyText,
  placeholder,
  context = [],
  onSend,
  title,
  showHeader = false,
  className,
}) {
  const { t } = useLanguage()
  const scrollRef = useRef(null)
  const { history, notices, decisions, pricing, input, setInput, sending, insufficientCredit } = chat

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [history, notices, insufficientCredit])

  const noticesAfter = (index) => notices.filter((notice) => notice.afterIndex === index)
  const disabled = insufficientCredit
  const canSend = !sending && !disabled && input.trim().length > 0

  return (
    <div className={cn('flex min-h-0 flex-1 flex-col', className)}>
      {showHeader ? (
        <div className="flex flex-none items-center gap-2.5 border-b border-border px-4 py-3.5">
          <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 className="text-lg font-bold text-foreground">{title}</h2>
        </div>
      ) : null}

      <div ref={scrollRef} className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {history.length === 0 ? <p className="text-sm text-muted-foreground">{emptyText}</p> : null}
        {noticesAfter(-1).map((notice) => (
          <Notice key={notice.id} notice={notice} />
        ))}
        {history.map((turn, messageIndex) => (
          <div key={messageIndex} className={cn('flex flex-col gap-2.5', turn.role === 'user' ? 'items-end' : 'items-start')}>
            {turn.message ? (
              <div
                className={cn(
                  'max-w-[85%] whitespace-pre-line break-words rounded-[18px] px-4 py-2.5 text-[15px] leading-snug',
                  turn.role === 'user' ? 'rounded-br-md bg-primary text-primary-foreground' : 'rounded-bl-md bg-secondary text-foreground',
                )}
              >
                {turn.message}
              </div>
            ) : null}
            {turn.actions?.length > 0 ? (
              <div className="flex w-[92%] flex-col gap-2.5">
                {turn.actions.map((action, actionIndex) => (
                  <ProposalCard
                    key={actionIndex}
                    action={action}
                    describe={describe}
                    decision={decisions[`${messageIndex}-${actionIndex}`]}
                    onDecide={(decision) => chat.decide(messageIndex, actionIndex, action, decision)}
                  />
                ))}
              </div>
            ) : null}
            {noticesAfter(messageIndex).map((notice) => (
              <Notice key={notice.id} notice={notice} />
            ))}
          </div>
        ))}
        {insufficientCredit ? (
          <Banner variant="error" icon={Minus} className="w-[92%]" data-testid="chat-credit-blocked">
            {t('cvEditor.chatErrorCredit')}
          </Banner>
        ) : null}
      </div>

      <div className="flex flex-none flex-col gap-2.5 border-t border-border px-4 pt-3 pb-[max(16px,calc(8px_+_env(safe-area-inset-bottom)))] lg:pb-4">
        <div className="flex flex-col gap-0.5">
          {pricing ? <PriceLine pricing={pricing} /> : null}
          <AiNotice className="text-[13px] leading-snug" />
        </div>
        {context.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[13px] text-muted-foreground">{t('cvEditor.chatFocusLabel')}</span>
            {context.map((item) => (
              <span
                key={item.key}
                className="inline-flex max-w-full items-center gap-1 rounded-full bg-primary-soft py-1 pl-3 pr-1 text-[13px] font-semibold text-primary"
              >
                <span className="min-w-0 truncate">{item.label}</span>
                <button
                  type="button"
                  onClick={item.onRemove}
                  aria-label={t('cvEditor.chatFocusRemove').replace('{text}', item.label)}
                  className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full outline-none hover:bg-tint focus-visible:ring-3 focus-visible:ring-ring/30"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </span>
            ))}
          </div>
        ) : null}
        <div className="flex items-end gap-2.5">
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <Textarea
              value={input}
              disabled={disabled}
              maxLength={MAX_CHAT_MESSAGE_LENGTH}
              aria-label={title}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  if (canSend) onSend()
                }
              }}
              placeholder={placeholder}
              className="min-h-14 resize-none"
              rows={2}
            />
            {input.length >= MAX_CHAT_MESSAGE_LENGTH - 300 ? (
              <span className="text-right text-xs tabular-nums text-muted-foreground">
                {input.length}/{MAX_CHAT_MESSAGE_LENGTH}
              </span>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onSend}
            disabled={!canSend}
            aria-label={sending ? t('cvEditor.chatSending') : t('cvEditor.chatSend')}
            className="mb-0.5 inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-button bg-primary text-primary-foreground outline-none hover:bg-primary/90 focus-visible:ring-3 focus-visible:ring-ring/30 disabled:opacity-45"
          >
            {sending ? <Spinner size={20} className="text-primary-foreground" /> : <ArrowUp className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </div>
    </div>
  )
}
