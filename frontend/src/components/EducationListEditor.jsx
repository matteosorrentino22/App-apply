import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import CityOnlyAutocomplete from '@/components/CityOnlyAutocomplete'

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

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1 text-base font-semibold text-foreground">{t('onboarding.educations')}</legend>
      {rows.map((row) => (
        <div key={row._key} className="flex flex-col gap-3 rounded-lg border border-border p-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex min-w-40 flex-1 flex-col gap-1.5">
              <Label htmlFor={`${row._key}-institution`}>{t('onboarding.institution')}</Label>
              <Input
                id={`${row._key}-institution`}
                value={row.institution}
                onChange={(e) => updateRow(row._key, { institution: e.target.value })}
              />
            </div>
            <div className="flex min-w-40 flex-1 flex-col gap-1.5">
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
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => removeRow(row._key)}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t('onboarding.remove')}
            </Button>
          </div>
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex min-w-32 flex-1 flex-col gap-1.5">
              <Label htmlFor={`${row._key}-start`}>{t('onboarding.startDate')}</Label>
              <Input
                id={`${row._key}-start`}
                type="date"
                value={row.start_date}
                onChange={(e) => updateRow(row._key, { start_date: e.target.value })}
              />
            </div>
            <div className="flex min-w-32 flex-1 flex-col gap-1.5">
              <Label htmlFor={`${row._key}-end`}>{t('onboarding.endDate')}</Label>
              <Input
                id={`${row._key}-end`}
                type="date"
                disabled={row.ongoing}
                value={row.end_date}
                onChange={(e) => updateRow(row._key, { end_date: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-2 pb-2 text-sm">
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
        </div>
      ))}
      <Button type="button" variant="secondary" size="sm" onClick={addRow} className="w-fit">
        {t('onboarding.addEducation')}
      </Button>
    </fieldset>
  )
}
