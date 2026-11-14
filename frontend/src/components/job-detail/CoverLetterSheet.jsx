import { useLanguage } from '../../i18n/LanguageContext'
import AiNotice from '../AiNotice'
import { Field } from '@/components/ui/field'
import { Sheet, SheetBody, SheetContent, SheetHeader } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { MAX_INSTRUCTIONS_LENGTH, joinInstructions } from '../../utils/generationLimits'
import { CharCountHint, GenerationFooter, PastInstructions } from './GenerationSheetParts'

// Genera cover letter (Sprint 75, mockup `detail-cover-letter`): stessi
// parametri della finestra di prima (indicazioni nuove + riuso di quelle
// passate, unite da una riga vuota). Il costo mostrato è quello della cover
// letter (prima dello Sprint 75 era, per errore, quello del messaggio).
export default function CoverLetterSheet({
  open,
  onOpenChange,
  text,
  onTextChange,
  pastInstructions,
  selectedPast,
  onTogglePast,
  usage,
  regenerate,
  onSubmit,
  busy,
}) {
  const { t } = useLanguage()
  const tooLong = joinInstructions(selectedPast, text).length > MAX_INSTRUCTIONS_LENGTH
  const title = regenerate ? t('jobs.regenerateCoverLetter') : t('jobs.coverLetterDialogTitle')
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader title={title} description={t('jobs.coverLetterDialogHint')} />
        <SheetBody className="pt-3">
          <Field
            label={t('jobs.coverLetterInstructionsLabel')}
            hint={<CharCountHint length={text.length} max={MAX_INSTRUCTIONS_LENGTH} />}
          >
            <Textarea
              id="cover-letter-instructions"
              value={text}
              maxLength={MAX_INSTRUCTIONS_LENGTH}
              onChange={(event) => onTextChange(event.target.value)}
              placeholder={t('jobs.coverLetterInstructionsPlaceholder')}
            />
          </Field>
          <PastInstructions
            label={t('jobs.coverLetterPastInstructionsLabel')}
            items={pastInstructions}
            selected={selectedPast}
            onToggle={onTogglePast}
          />
          <AiNotice className="text-center text-[13px]" />
        </SheetBody>
        <GenerationFooter
          usage={usage}
          action="cover_letter"
          submitLabel={title}
          onSubmit={onSubmit}
          disabled={busy || tooLong}
          reason={tooLong ? t('jobs.instructionsTooLong').replace('{max}', MAX_INSTRUCTIONS_LENGTH) : null}
        />
      </SheetContent>
    </Sheet>
  )
}
