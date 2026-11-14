import { Link2 } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import AiNotice from '../AiNotice'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SegmentedControl } from '@/components/ui/segmented'
import { Sheet, SheetBody, SheetContent, SheetHeader } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import {
  MAX_INSTRUCTIONS_LENGTH,
  MAX_RECIPIENT_LINKEDIN_URL_LENGTH,
  MAX_RECIPIENT_NAME_LENGTH,
  joinInstructions,
} from '../../utils/generationLimits'
import { CharCountHint, GenerationFooter, PastInstructions } from './GenerationSheetParts'

// Genera messaggio di networking (Sprint 75, mockup `detail-message`): stessi
// campi della finestra di prima. Il costo mostrato è quello del messaggio
// (prima dello Sprint 75 era, per errore, quello della cover letter).
export default function ReferralSheet({ open, onOpenChange, form, onFormChange, pastInstructions, selectedPast, onTogglePast, usage, onSubmit, busy }) {
  const { t } = useLanguage()
  const set = (key) => (event) => onFormChange({ ...form, [key]: event.target.value })
  const tooLong = joinInstructions(selectedPast, form.instructions).length > MAX_INSTRUCTIONS_LENGTH
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader title={t('jobs.referralDialogTitle')} description={t('jobs.referralDialogHint')} />
        <SheetBody className="pt-3">
          <div className="flex flex-col gap-1.5">
            <p aria-hidden="true" className="text-[13px] font-semibold leading-snug text-label">
              {t('jobs.referralChannelLabel')}
            </p>
            <SegmentedControl
              name="referral-channel"
              label={t('jobs.referralChannelLabel')}
              value={form.channel}
              onChange={(channel) => onFormChange({ ...form, channel })}
              options={[
                { value: 'linkedin', label: t('jobs.referralChannelLinkedin') },
                { value: 'email', label: t('jobs.referralChannelEmail') },
              ]}
            />
          </div>
          <Field label={t('jobs.referralRecipientNameLabel')}>
            <Input
              id="referral-recipient-name"
              value={form.recipientName}
              maxLength={MAX_RECIPIENT_NAME_LENGTH}
              onChange={set('recipientName')}
              placeholder={t('jobs.referralRecipientNamePlaceholder')}
            />
          </Field>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="referral-recipient-linkedin">{t('jobs.referralRecipientLinkedinLabel')}</Label>
            <div className="relative">
              <Link2
                className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                id="referral-recipient-linkedin"
                className="pl-11"
                inputMode="url"
                aria-describedby="referral-recipient-linkedin-hint"
                value={form.recipientLinkedinUrl}
                maxLength={MAX_RECIPIENT_LINKEDIN_URL_LENGTH}
                onChange={set('recipientLinkedinUrl')}
                placeholder={t('jobs.referralRecipientLinkedinPlaceholder')}
              />
            </div>
            <p id="referral-recipient-linkedin-hint" className="text-xs leading-snug text-muted-foreground">
              {t('jobs.referralRecipientLinkedinHint')}
            </p>
          </div>
          <Field
            label={t('jobs.referralInstructionsLabel')}
            hint={<CharCountHint length={form.instructions.length} max={MAX_INSTRUCTIONS_LENGTH} />}
          >
            <Textarea
              id="referral-instructions"
              value={form.instructions}
              maxLength={MAX_INSTRUCTIONS_LENGTH}
              onChange={set('instructions')}
              placeholder={t('jobs.referralInstructionsPlaceholder')}
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
          action="referral_message"
          submitLabel={t('jobs.generateReferralMessage')}
          onSubmit={onSubmit}
          disabled={busy || tooLong}
          reason={tooLong ? t('jobs.instructionsTooLong').replace('{max}', MAX_INSTRUCTIONS_LENGTH) : null}
        />
      </SheetContent>
    </Sheet>
  )
}
