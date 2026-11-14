import { cva } from 'class-variance-authority'
import { useLanguage } from '@/i18n/LanguageContext'
import { cn } from '@/lib/utils'
import { scoreStyle } from '@/utils/scoreStyle'

// Chip del punteggio a fasce (DESIGN.md §3.1): 44×44 in lista, 56×56 nel
// dettaglio. La fascia è quella esistente (utils/scoreStyle.js, 2 valori
// per colore); senza punteggio un chip neutro con "–".
const scoreChipVariants = cva('flex shrink-0 items-center justify-center font-bold tabular-nums', {
  variants: {
    size: {
      md: 'h-11 w-11 rounded-field text-xl',
      lg: 'h-14 w-14 rounded-card text-[26px]',
    },
  },
  defaultVariants: { size: 'md' },
})

function ScoreChip({ score, size = 'md', className }) {
  const { t } = useLanguage()
  const hasScore = typeof score === 'number'
  const label = hasScore ? t('common.scoreLabel').replace('{score}', score) : t('common.scoreNone')
  return (
    <div
      role="img"
      aria-label={label}
      title={label}
      className={cn(scoreChipVariants({ size }), hasScore ? scoreStyle(score) : 'bg-chip text-chip-foreground', className)}
    >
      <span aria-hidden="true">{hasScore ? score : '–'}</span>
    </div>
  )
}

export { ScoreChip }
