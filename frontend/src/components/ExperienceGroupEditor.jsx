import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import ChipInput from '@/components/ChipInput'

let nextKey = 0
function makeKey() {
  nextKey += 1
  return `exp-${nextKey}`
}

export function emptyRole() {
  return { _key: makeKey(), role: '', location: '', bullets: [] }
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
export default function ExperienceGroupEditor({ companies, onChange, t }) {
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
    <fieldset className="flex flex-col gap-4">
      <legend className="mb-1 text-base font-semibold text-foreground">{t('onboarding.experiences')}</legend>
      <p className="-mt-2 text-sm text-muted-foreground">{t('onboarding.experiencesHint')}</p>

      {companies.map((c) => (
        <Card key={c._key} className="p-5">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div className="flex max-w-sm flex-1 flex-col gap-1.5">
              <Label htmlFor={`company-${c._key}`}>{t('onboarding.company')}</Label>
              <Input
                id={`company-${c._key}`}
                value={c.company}
                onChange={(e) => updateCompany(c._key, { company: e.target.value })}
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => removeCompany(c._key)}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t('onboarding.removeCompany')}
            </Button>
          </div>

          <div className="flex flex-col">
            {c.roles.map((r, index) => (
              <div key={r._key} className="flex gap-3">
                <div className="flex w-4 shrink-0 flex-col items-center">
                  <span className="mt-[26px] h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />
                  {index < c.roles.length - 1 && <span className="mt-1 w-0.5 flex-1 bg-border" />}
                </div>
                <div className={cnPad(index, c.roles.length)}>
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex flex-1 flex-wrap gap-4">
                      <div className="flex max-w-60 flex-1 flex-col gap-1.5">
                        <Label htmlFor={`role-${r._key}`}>{t('onboarding.role')}</Label>
                        <Input
                          id={`role-${r._key}`}
                          value={r.role}
                          onChange={(e) => updateRole(c._key, r._key, { role: e.target.value })}
                        />
                      </div>
                      <div className="flex max-w-60 flex-1 flex-col gap-1.5">
                        <Label htmlFor={`role-location-${r._key}`}>{t('onboarding.location')}</Label>
                        <Input
                          id={`role-location-${r._key}`}
                          value={r.location}
                          onChange={(e) => updateRole(c._key, r._key, { location: e.target.value })}
                        />
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeRole(c._key, r._key)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      {t('onboarding.removeRole')}
                    </Button>
                  </div>
                  <div className="mt-3 flex flex-col gap-1.5">
                    <Label htmlFor={`activities-${r._key}`}>{t('onboarding.activities')}</Label>
                    <ChipInput
                      id={`activities-${r._key}`}
                      value={r.bullets}
                      onChange={(bullets) => updateRole(c._key, r._key, { bullets })}
                      placeholder={t('onboarding.activitiesPlaceholder')}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <Button type="button" variant="secondary" size="sm" className="mt-3" onClick={() => addRole(c._key)}>
            {t('onboarding.addRole')}
          </Button>
        </Card>
      ))}

      <Button type="button" variant="secondary" onClick={addCompany} className="w-fit">
        {t('onboarding.addCompany')}
      </Button>
    </fieldset>
  )
}

function cnPad(index, total) {
  return index < total - 1 ? 'flex-1 pb-5' : 'flex-1'
}
