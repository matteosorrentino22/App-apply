import { useLanguage } from '../../i18n/LanguageContext'
import AiNotice from '../AiNotice'
import { Checkbox } from '@/components/ui/checkbox'
import { Field } from '@/components/ui/field'
import { Sheet, SheetBody, SheetContent, SheetHeader } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { scoreItemLabel, scoreItemReason } from '../../utils/scoreItems'
import { MAX_INSTRUCTIONS_LENGTH } from '../../utils/generationLimits'
import { CharCountHint, GenerationFooter } from './GenerationSheetParts'

// "Colma i gap" (Sprint 75, SPEC-DELTA A3, mockup `detail-gap`): passo
// facoltativo che si apre a ogni "Genera CV" / "Rigenera CV". Stessi dati
// di prima (Sprint 69): i gap selezionati sono i loro numeri nell'elenco
// (1-based), gli stessi mostrati qui e usati dal server nel prompt.
export default function GapSheet({
  open,
  onOpenChange,
  gaps,
  selectedGaps,
  onToggleGap,
  instructions,
  onInstructionsChange,
  usage,
  regenerate,
  onSubmit,
  busy,
}) {
  const { t } = useLanguage()
  const title = regenerate ? t('jobs.regenerateCv') : t('jobs.generateCv')
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader title={title} description={t('jobs.gapPanelHint')} />
        <SheetBody className="pt-3">
          {gaps.length > 0 ? (
            <div className="flex flex-col gap-3">
              {gaps.map((item, index) => {
                const number = index + 1
                const reason = scoreItemReason(item)
                return (
                  <label key={index} className="flex cursor-pointer items-start gap-3 text-base text-foreground">
                    <Checkbox
                      className="mt-px"
                      checked={selectedGaps.includes(number)}
                      onCheckedChange={() => onToggleGap(number)}
                    />
                    <span className="flex min-w-0 flex-col gap-0.5">
                      <span>
                        {number}. {scoreItemLabel(item)}
                      </span>
                      {reason ? <span className="text-sm text-muted-foreground">{reason}</span> : null}
                    </span>
                  </label>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t('jobs.gapPanelNoGaps')}</p>
          )}
          <Field
            label={t('jobs.gapInstructionsLabel')}
            hint={
              <CharCountHint length={instructions.length} max={MAX_INSTRUCTIONS_LENGTH}>
                {selectedGaps.length > 0 && !instructions.trim() ? t('jobs.gapInstructionsDefaultHint') : null}
              </CharCountHint>
            }
          >
            <Textarea
              id="gap-instructions"
              value={instructions}
              maxLength={MAX_INSTRUCTIONS_LENGTH}
              onChange={(event) => onInstructionsChange(event.target.value)}
              placeholder={t('jobs.gapInstructionsPlaceholder')}
            />
          </Field>
          <AiNotice className="text-center text-[13px]" />
        </SheetBody>
        <GenerationFooter usage={usage} action="cv" submitLabel={title} onSubmit={onSubmit} disabled={busy} />
      </SheetContent>
    </Sheet>
  )
}
