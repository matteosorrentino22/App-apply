import { MapPin, Save, X } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FilterPill } from '@/components/ui/pill'
import { SegmentedControl } from '@/components/ui/segmented'
import { Sheet, SheetBody, SheetClose, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { APPLICANTS_RANGES, SCORES, STATUSES } from '../utils/jobFilters'

// Pannello dei filtri della lista (Sprint 74, mockup `jobs-filtri`; da
// 1024 px finestra centrale). Stessi filtri e stessa logica di prima: i
// valori restano nella query string (Sprint 68) e si applicano subito,
// "Mostra risultati" chiude il pannello. Le date non fanno parte dei filtri
// salvati (come prima). Il filtro "Ricerca di provenienza" non c'è nella
// sezione Importati (i job importati non hanno una ricerca di provenienza).


function Group({ title, children, className }) {
  return (
    <fieldset className={cn('flex min-w-0 flex-col gap-2.5', className)}>
      <legend className="mb-2.5 text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{title}</legend>
      {children}
    </fieldset>
  )
}

// Aggiornamento "funzionale" (vedi updateParams di JobListPage): parte dal
// valore attuale nell'URL, non da quello dell'ultimo render.
function toggle(value) {
  const item = String(value)
  return (list) => (list.includes(item) ? list.filter((current) => current !== item) : [...list, item])
}

export default function JobFiltersSheet({
  open,
  onOpenChange,
  section,
  filters,
  onChange,
  locationInput,
  onLocationChange,
  savedSearches,
  presets,
  onApplyPreset,
  onDeletePreset,
  onSavePreset,
  onReset,
}) {
  const { t } = useLanguage()
  const { dateFrom, dateTo, statuses, searchFilters, scores, applicantsRanges, recruiterFilter } = filters

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader title={t('jobs.filtersTitle')} />
        <SheetBody className="gap-6">
          <div className="flex flex-col gap-3 border-b border-border pb-5">
            <p className="text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{t('jobs.savedFiltersTitle')}</p>
            {presets.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {presets.map((preset) => (
                  <span key={preset.id} className="flex min-h-10 items-center rounded-full bg-secondary pl-3.5 pr-1 text-[14px] font-semibold text-chip-foreground">
                    <button type="button" onClick={() => onApplyPreset(preset)} className="min-h-10 rounded-full outline-none focus-visible:ring-3 focus-visible:ring-ring/30">
                      {preset.name}
                    </button>
                    <button
                      type="button"
                      onClick={() => onDeletePreset(preset)}
                      aria-label={`${t('jobs.deletePreset')}: ${preset.name}`}
                      className="ml-0.5 flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground outline-none hover:text-destructive focus-visible:ring-3 focus-visible:ring-ring/30"
                    >
                      <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <Button variant="secondary" className="w-full" onClick={onSavePreset}>
              <Save className="h-[18px] w-[18px]" aria-hidden="true" />
              {t('jobs.savePresetButton')}
            </Button>
          </div>

          <Group title={t('jobs.datesGroupTitle')}>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex min-w-0 flex-col gap-1.5">
                <span className="text-[13px] font-semibold text-label">{t('jobs.dateFromLabel')}</span>
                <Input type="date" value={dateFrom} onChange={(event) => onChange({ from: event.target.value })} className="px-3" />
              </label>
              <label className="flex min-w-0 flex-col gap-1.5">
                <span className="text-[13px] font-semibold text-label">{t('jobs.dateToLabel')}</span>
                <Input type="date" value={dateTo} onChange={(event) => onChange({ to: event.target.value })} className="px-3" />
              </label>
            </div>
            {(dateFrom || dateTo) && (
              <button
                type="button"
                onClick={() => onChange({ from: '', to: '' })}
                className="self-start text-sm font-semibold text-primary underline-offset-2 hover:underline"
              >
                {t('jobs.dateRangeAll')}
              </button>
            )}
          </Group>

          <Group title={t('jobs.locationGroupTitle')}>
            <div className="relative">
              <MapPin className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                value={locationInput}
                onChange={(event) => onLocationChange(event.target.value)}
                placeholder={t('jobs.locationFilterPlaceholder')}
                aria-label={t('jobs.locationFilterPlaceholder')}
                className="pl-11"
              />
            </div>
          </Group>

          <Group title={t('jobs.statusLabel')}>
            <div className="flex flex-wrap gap-2">
              {STATUSES.map((value) => (
                <FilterPill key={value} pressed={statuses.includes(value)} onClick={() => onChange({ status: toggle(value) })}>
                  {t(`jobs.status_${value}`)}
                </FilterPill>
              ))}
            </div>
          </Group>

          {section !== 'imported' && (
            <Group title={t('jobs.searchGroupTitle')}>
              <div className="flex flex-wrap gap-2">
                {savedSearches.map((search) => (
                  <FilterPill
                    key={search.id}
                    pressed={searchFilters.includes(String(search.id))}
                    onClick={() => onChange({ search: toggle(String(search.id)) })}
                    className="h-auto whitespace-normal py-2 text-left leading-snug"
                    title={`${t(`account.searchType_${search.search_type}`)}: ${search.keywords} — ${search.city}, ${search.country}`}
                  >
                    {search.keywords} · {search.city}
                  </FilterPill>
                ))}
                <FilterPill pressed={searchFilters.includes('none')} onClick={() => onChange({ search: toggle('none') })}>
                  {t('jobs.searchFilter_none')}
                </FilterPill>
              </div>
            </Group>
          )}

          <Group title={t('jobs.scoreLabel')}>
            <div className="flex flex-wrap gap-2">
              {SCORES.map((value) => (
                <FilterPill
                  key={value}
                  pressed={scores.includes(value)}
                  onClick={() => onChange({ score: toggle(value) })}
                  className="w-11 px-0 tabular-nums"
                >
                  {value}
                </FilterPill>
              ))}
            </div>
          </Group>

          <Group title={t('jobs.applicantsLabel')}>
            <div className="flex flex-wrap gap-2">
              {APPLICANTS_RANGES.map((value) => (
                <FilterPill
                  key={value}
                  pressed={applicantsRanges.includes(value)}
                  onClick={() => onChange({ applicants: toggle(value) })}
                >
                  {t(`jobs.applicants_${value}`)}
                </FilterPill>
              ))}
            </div>
          </Group>

          <Group title={t('jobs.recruiterFilterLabel')}>
            <SegmentedControl
              name="recruiter-filter"
              label={t('jobs.recruiterFilterLabel')}
              value={recruiterFilter}
              onChange={(value) => onChange({ recruiter: value === 'all' ? '' : value })}
              options={[
                { value: 'all', label: t('jobs.recruiterFilter_all') },
                { value: 'yes', label: t('jobs.recruiterFilter_yes') },
                { value: 'no', label: t('jobs.recruiterFilter_no') },
              ]}
            />
          </Group>
        </SheetBody>
        <SheetFooter>
          <SheetClose asChild>
            <Button size="lg">{t('jobs.showResults')}</Button>
          </SheetClose>
          <Button variant="text" onClick={onReset}>
            {t('jobs.resetFilters')}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
