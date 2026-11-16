import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card } from '@/components/ui/card'
import { DateRangeFields } from '@/components/ui/date-range'
import ActivityChipsInput from '@/components/ActivityChipsInput'
import ChipInput from '@/components/ChipInput'
import CityOnlyAutocomplete from '@/components/CityOnlyAutocomplete'

// Stessi limiti del backend (apps/profiles/serializers.py, Sprint 70).
// Sprint 78: solo stile. Sprint 81: impaginazione rifatta (props, dati e
// comportamento invariati): campi a tutta larghezza, ogni ruolo in un
// riquadro, date con DateRangeFields, azioni come pulsanti di testo da 44 px.
const MAX_BULLETS = 15
const MAX_BULLET_LENGTH = 400
const MAX_TECHNOLOGY_LENGTH = 200

let nextKey = 0
function makeKey() {
  nextKey += 1
  return `exp-${nextKey}`
}

export function emptyRole() {
  return {
    _key: makeKey(),
    role: '',
    location: '',
    location_country_code: '',
    start_date: '',
    end_date: '',
    ongoing: false,
    bullets: [],
    technologies: [],
  }
}

export function emptyCompany() {
  return { _key: makeKey(), company: '', roles: [emptyRole()] }
}

/**
 * Un'azienda può comparire una sola volta con più ruoli annidati sotto
 * (stesso pattern "più posizioni" di LinkedIn): evita di far riscrivere il
 * nome azienda per ogni ruolo. In salvataggio ogni ruolo resta comunque
 * un'esperienza indipendente (azienda + ruolo + località + attività) — il
 * raggruppamento è solo come il form lo presenta, non cosa viene inviato.
 */
export default function ExperienceGroupEditor({
  companies,
  onChange,
  t,
  titleKey = 'onboarding.experiences',
  hintKey = 'onboarding.experiencesHint',
}) {
  function updateCompany(companyKey, patch) {
    onChange(companies.map((c) => (c._key === companyKey ? { ...c, ...patch } : c)))
  }

  function updateRole(companyKey, roleKey, patch) {
    onChange(
      companies.map((c) =>
        c._key === companyKey
          ? { ...c, roles: c.roles.map((r) => (r._key === roleKey ? { ...r, ...patch } : r)) }
          : c,
      ),
    )
  }

  function addRole(companyKey) {
    onChange(
      companies.map((c) => (c._key === companyKey ? { ...c, roles: [...c.roles, emptyRole()] } : c)),
    )
  }

  function removeRole(companyKey, roleKey) {
    onChange(
      companies.map((c) =>
        c._key === companyKey ? { ...c, roles: c.roles.filter((r) => r._key !== roleKey) } : c,
      ),
    )
  }

  function removeCompany(companyKey) {
    onChange(companies.filter((c) => c._key !== companyKey))
  }

  function addCompany() {
    onChange([...companies, emptyCompany()])
  }

  return (
    <fieldset className="flex min-w-0 flex-col gap-4">
      <legend className="mb-1 text-base font-semibold text-foreground">{t(titleKey)}</legend>
      <p className="-mt-2 text-sm text-muted-foreground">{t(hintKey)}</p>

      {companies.map((c) => (
        <Card key={c._key} className="flex min-w-0 flex-col gap-6 p-4 sm:p-5" data-testid="experience-company">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor={`company-${c._key}`}>{t('onboarding.company')}</Label>
            <Input
              id={`company-${c._key}`}
              value={c.company}
              onChange={(e) => updateCompany(c._key, { company: e.target.value })}
            />
          </div>

          <div className="flex flex-col gap-4">
            {c.roles.map((r) => (
              // Sprint 81: ogni ruolo in un riquadro leggero a tutta larghezza
              // (prima rientrato con un puntino: a 360 px i campi si
              // stringevano e "Data fine" usciva dalla card).
              <div key={r._key} className="flex min-w-0 flex-col gap-4 rounded-field border border-border bg-tint p-3 sm:p-4" data-testid="experience-role">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor={`role-${r._key}`}>{t('onboarding.role')}</Label>
                  <Input
                    id={`role-${r._key}`}
                    value={r.role}
                    onChange={(e) => updateRole(c._key, r._key, { role: e.target.value })}
                  />
                </div>
                <CityOnlyAutocomplete
                  cityId={`role-location-${r._key}`}
                  label={t('onboarding.location')}
                  city={r.location}
                  onChange={({ city, countryCode }) =>
                    updateRole(c._key, r._key, {
                      location: city,
                      location_country_code: countryCode ?? r.location_country_code,
                    })
                  }
                />
                <div className="flex flex-col gap-1">
                  <DateRangeFields
                    startId={`role-start-${r._key}`}
                    endId={`role-end-${r._key}`}
                    startLabel={t('onboarding.startDate')}
                    endLabel={t('onboarding.endDate')}
                    start={r.start_date}
                    end={r.end_date}
                    endDisabled={r.ongoing}
                    onStartChange={(value) => updateRole(c._key, r._key, { start_date: value })}
                    onEndChange={(value) => updateRole(c._key, r._key, { end_date: value })}
                  />
                  <label className="flex min-h-11 w-fit cursor-pointer items-center gap-3 text-[15px] text-foreground">
                    <Checkbox
                      checked={r.ongoing}
                      onCheckedChange={(checked) =>
                        updateRole(c._key, r._key, {
                          ongoing: checked === true,
                          end_date: checked === true ? '' : r.end_date,
                        })
                      }
                    />
                    {t('onboarding.ongoing')}
                  </label>
                </div>
                <div className="flex flex-col gap-1.5">
                  {/* Sprint 82: attività come chip modificabili (A15), con il
                      contatore "n / 15"; le tecnologie restano su ChipInput. */}
                  <div className="flex items-baseline justify-between gap-3">
                    <Label htmlFor={`activities-${r._key}`}>{t('onboarding.activities')}</Label>
                    <span className="shrink-0 text-[13px] tabular-nums text-muted-foreground" aria-hidden="true">
                      {r.bullets.length} / {MAX_BULLETS}
                    </span>
                  </div>
                  <ActivityChipsInput
                    id={`activities-${r._key}`}
                    value={r.bullets}
                    onChange={(bullets) => updateRole(c._key, r._key, { bullets })}
                    placeholder={t('onboarding.activitiesPlaceholder')}
                    maxLength={MAX_BULLET_LENGTH}
                    maxItems={MAX_BULLETS}
                    flagTooLong={typeof r._key !== 'number'}
                    describedBy={`activities-hint-${r._key}`}
                  />
                  <p id={`activities-hint-${r._key}`} className="text-xs leading-snug text-muted-foreground">
                    {r.bullets.length >= MAX_BULLETS
                      ? t('profileExtras.activitiesMaxHint')
                      : `${r.bullets.length > 0 ? `${t('profileExtras.activitiesTapHint')} ` : ''}${t('profileExtras.bulletsHint')
                          .replace('{max}', MAX_BULLETS)
                          .replace('{length}', MAX_BULLET_LENGTH)}`}
                  </p>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor={`technologies-${r._key}`}>{t('profileExtras.technologies')}</Label>
                  <ChipInput
                    id={`technologies-${r._key}`}
                    value={r.technologies || []}
                    onChange={(technologies) => updateRole(c._key, r._key, { technologies })}
                    placeholder={t('profileExtras.technologiesPlaceholder')}
                    maxLength={MAX_TECHNOLOGY_LENGTH}
                  />
                </div>
                <Button
                  type="button"
                  variant="text"
                  onClick={() => removeRole(c._key, r._key)}
                  className="-ml-2 self-start px-2 text-destructive-text hover:bg-destructive-soft"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  {t('onboarding.removeRole')}
                </Button>
              </div>
            ))}
          </div>

          <div className="flex flex-col items-start gap-1">
            <Button type="button" variant="text" className="-ml-2 px-2 text-left" onClick={() => addRole(c._key)}>
              <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
              {t('onboarding.addRole')}
            </Button>
            <Button
              type="button"
              variant="text"
              onClick={() => removeCompany(c._key)}
              className="-ml-2 px-2 text-destructive-text hover:bg-destructive-soft"
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {t('onboarding.removeCompany')}
            </Button>
          </div>
        </Card>
      ))}

      <Button type="button" variant="secondary" onClick={addCompany} className="w-fit">
        <Plus className="h-4 w-4" aria-hidden="true" />
        {t('onboarding.addCompany')}
      </Button>
    </fieldset>
  )
}
