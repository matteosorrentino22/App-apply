import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import CityOnlyAutocomplete from '@/components/CityOnlyAutocomplete'
import { DateRangeFields } from '@/components/ui/date-range'

let nextKey = 0
function makeKey() {
  nextKey += 1
  return `edu-${nextKey}`
}

export function emptyEducationRow() {
  return {
    _key: makeKey(),
    institution: '',
    title: '',
    location: '',
    location_country_code: '',
    start_date: '',
    end_date: '',
    ongoing: false,
    notes: '',
  }
}

/**
 * Editor dedicato all'istruzione (a differenza delle altre sezioni a righe
 * semplici — competenze/certificazioni/lingue, coperte da
 * ListSectionEditor): serve l'autocomplete città e la spunta "in corso" per
 * `end_date` (Sprint 34), non esprimibili con la config a campi generici.
 */
export default function EducationListEditor({ rows, onChange, t }) {
  function updateRow(key, patch) {
    onChange(rows.map((row) => (row._key === key ? { ...row, ...patch } : row)))
  }

  function addRow() {
    onChange([...rows, emptyEducationRow()])
  }

  function removeRow(key) {
    onChange(rows.filter((row) => row._key !== key))
  }

  // Sprint 81: stessa impaginazione delle esperienze (campi a tutta
  // larghezza, date con DateRangeFields, azioni come pulsanti di testo).
  return (
    <fieldset className="flex min-w-0 flex-col gap-4">
      <legend className="mb-1 text-base font-semibold text-foreground">{t('onboarding.educations')}</legend>
      {rows.map((row) => (
        <div key={row._key} className="flex min-w-0 flex-col gap-4 rounded-field border border-border bg-tint p-3 sm:p-4" data-testid="education-row">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`${row._key}-institution`}>{t('onboarding.institution')}</Label>
            <Input
              id={`${row._key}-institution`}
              value={row.institution}
              onChange={(e) => updateRow(row._key, { institution: e.target.value })}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`${row._key}-title`}>{t('onboarding.titleField')}</Label>
            <Input
              id={`${row._key}-title`}
              value={row.title}
              onChange={(e) => updateRow(row._key, { title: e.target.value })}
            />
          </div>
          <CityOnlyAutocomplete
            cityId={`${row._key}-location`}
            label={t('onboarding.location')}
            city={row.location}
            onChange={({ city, countryCode }) =>
              updateRow(row._key, {
                location: city,
                location_country_code: countryCode ?? row.location_country_code,
              })
            }
          />
          <div className="flex flex-col gap-1">
            <DateRangeFields
              startId={`${row._key}-start`}
              endId={`${row._key}-end`}
              startLabel={t('onboarding.startDate')}
              endLabel={t('onboarding.endDate')}
              start={row.start_date}
              end={row.end_date}
              endDisabled={row.ongoing}
              onStartChange={(value) => updateRow(row._key, { start_date: value })}
              onEndChange={(value) => updateRow(row._key, { end_date: value })}
            />
            <label className="flex min-h-11 w-fit cursor-pointer items-center gap-3 text-[15px] text-foreground">
              <Checkbox
                checked={row.ongoing}
                onCheckedChange={(checked) =>
                  updateRow(row._key, {
                    ongoing: checked === true,
                    end_date: checked === true ? '' : row.end_date,
                  })
                }
              />
              {t('onboarding.ongoing')}
            </label>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`${row._key}-notes`}>{t('onboarding.notes')}</Label>
            <Input
              id={`${row._key}-notes`}
              value={row.notes}
              onChange={(e) => updateRow(row._key, { notes: e.target.value })}
            />
          </div>
          <Button
            type="button"
            variant="text"
            onClick={() => removeRow(row._key)}
            className="-ml-2 self-start px-2 text-destructive-text hover:bg-destructive-soft"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {t('onboarding.remove')}
          </Button>
        </div>
      ))}
      <Button type="button" variant="secondary" onClick={addRow} className="w-fit">
        <Plus className="h-4 w-4" aria-hidden="true" />
        {t('onboarding.addEducation')}
      </Button>
    </fieldset>
  )
}
