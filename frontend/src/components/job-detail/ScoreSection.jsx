import { Check, ChevronDown, ChevronUp, Minus } from 'lucide-react'
import { useId, useState } from 'react'
import { useLanguage } from '../../i18n/LanguageContext'
import { CounterToggle } from '@/components/ui/counter-toggle'
import { ExpandableText } from '@/components/ui/expandable-text'
import { scoreItemLabel, scoreItemReason } from '../../utils/scoreItems'

// "Perché questo punteggio" + contatori corrispondenze/gap (Sprint 75,
// mockup `detail-nuovo`): motivazione troncata con "Leggi tutto"; un
// contatore aperto per volta, elenco sotto con etichetta e motivo di ogni
// voce (prima dietro "Espandi motivazioni"). I due contatori stanno
// affiancati se c'è spazio (desktop), altrimenti uno sotto l'altro.
function ItemList({ id, items, tone }) {
  const Icon = tone === 'success' ? Check : Minus
  return (
    <ul id={id} className="flex flex-col gap-1 rounded-field bg-secondary p-3">
      {items.map((item, index) => {
        const reason = scoreItemReason(item)
        return (
          <li key={index} className="flex gap-2.5 py-1 text-base text-foreground">
            <Icon
              className={tone === 'success' ? 'mt-0.5 h-5 w-5 shrink-0 text-success' : 'mt-0.5 h-5 w-5 shrink-0 text-destructive'}
              strokeWidth={2.4}
              aria-hidden="true"
            />
            <span className="flex min-w-0 flex-col gap-0.5">
              <span className="break-words">{scoreItemLabel(item)}</span>
              {reason ? <span className="text-sm text-muted-foreground">{reason}</span> : null}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

export function ScoreSection({ job }) {
  const { t } = useLanguage()
  const [open, setOpen] = useState(null)
  const listId = useId()
  const matches = job.score_match || []
  const gaps = job.score_gaps || []
  if (!job.score_reasoning && matches.length === 0 && gaps.length === 0) return null

  const toggle = (key) => setOpen((current) => (current === key ? null : key))
  return (
    <section aria-labelledby="score-title" className="flex flex-col gap-3 rounded-card border border-border bg-card p-4 shadow-card">
      <h2 id="score-title" className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
        {t('jobs.whyThisScore')}
      </h2>
      {job.score_reasoning ? <ExpandableText text={job.score_reasoning} className="text-base leading-normal text-foreground" /> : null}
      {matches.length > 0 || gaps.length > 0 ? (
        <div className="flex flex-wrap gap-2.5">
          {matches.length > 0 ? (
            <CounterToggle
              tone="success"
              className="flex-[1_1_15rem]"
              count={matches.length}
              label={matches.length === 1 ? t('jobs.matchesCountOne') : t('jobs.matchesCountMany')}
              expanded={open === 'match'}
              controls={open === 'match' ? listId : undefined}
              onClick={() => toggle('match')}
            />
          ) : null}
          {gaps.length > 0 ? (
            <CounterToggle
              tone="destructive"
              className="flex-[1_1_8rem]"
              count={gaps.length}
              label={gaps.length === 1 ? t('jobs.gapsCountOne') : t('jobs.gapsCountMany')}
              expanded={open === 'gaps'}
              controls={open === 'gaps' ? listId : undefined}
              onClick={() => toggle('gaps')}
            />
          ) : null}
        </div>
      ) : null}
      {open === 'match' ? <ItemList id={listId} items={matches} tone="success" /> : null}
      {open === 'gaps' ? <ItemList id={listId} items={gaps} tone="destructive" /> : null}
    </section>
  )
}

// Descrizione dell'annuncio a fisarmonica (SPEC-DELTA A7, mockup
// `detail-nuovo`): chiusa all'apertura della pagina.
export function DescriptionSection({ description }) {
  const { t } = useLanguage()
  const [open, setOpen] = useState(false)
  const panelId = useId()
  if (!description) return null
  const Chevron = open ? ChevronUp : ChevronDown
  return (
    <section className="rounded-card border border-border bg-card shadow-card">
      <h2>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((current) => !current)}
          className="flex min-h-14 w-full items-center justify-between gap-3 rounded-card px-4 py-3 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/30"
        >
          <span className="text-base font-bold text-foreground">{t('jobs.description')}</span>
          <span className="flex shrink-0 items-center gap-1 text-[15px] font-semibold text-primary">
            {open ? t('jobs.descriptionHide') : t('jobs.descriptionShow')}
            <Chevron className="h-4 w-4" aria-hidden="true" />
          </span>
        </button>
      </h2>
      {open ? (
        <div id={panelId} className="border-t border-border px-4 pb-4 pt-3">
          <p className="whitespace-pre-line break-words text-[15px] leading-relaxed text-foreground">{description}</p>
        </div>
      ) : null}
    </section>
  )
}
