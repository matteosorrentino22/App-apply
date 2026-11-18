import { useState } from 'react'
import { useLanguage } from '../../i18n/LanguageContext'
import { SettingsSubpageHeader } from '@/components/settings/SettingsList'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { getTextSize, setTextSize, TEXT_SIZES } from '@/lib/textSize'

// Dimensione del testo (Sprint 84, SPEC-DELTA A20, mockup
// `settings-dimensione-testo`): Come il telefono / Normale / Grande, salvata
// sul dispositivo e applicata subito a tutta l'app (lib/textSize.js).
export default function TextSizePage() {
  const { t } = useLanguage()
  const [size, setSize] = useState(getTextSize)

  function choose(next) {
    setSize(next)
    setTextSize(next)
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 pb-6 pt-3 lg:pt-6">
      <SettingsSubpageHeader title={t('textSize.title')} description={t('textSize.description')} />
      <RadioGroup
        value={size}
        onValueChange={choose}
        name="text-size"
        aria-label={t('textSize.title')}
        className="flex flex-col gap-0 divide-y divide-border overflow-hidden rounded-card border border-border bg-card shadow-card"
      >
        {TEXT_SIZES.map((value) => (
          <label key={value} className="flex min-h-16 cursor-pointer items-center gap-3.5 px-4 py-3 hover:bg-tint">
            <RadioGroupItem value={value} aria-describedby={`text-size-${value}-hint`} />
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="text-base font-semibold leading-tight text-foreground">{t(`textSize.option_${value}`)}</span>
              <span id={`text-size-${value}-hint`} className="text-sm leading-snug text-muted-foreground">
                {t(`textSize.option_${value}_hint`)}
              </span>
            </span>
          </label>
        ))}
      </RadioGroup>
      <section aria-label={t('textSize.preview')} className="flex flex-col gap-2 rounded-card border border-border bg-card p-4 shadow-card">
        <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-muted-foreground">{t('textSize.preview')}</span>
        <span className="text-base font-[650] text-foreground">{t('textSize.previewTitle')}</span>
        <span className="text-sm text-muted-foreground">{t('textSize.previewSubtitle')}</span>
      </section>
    </div>
  )
}
