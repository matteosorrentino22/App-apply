import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { useLanguage } from '../../i18n/LanguageContext'
import { updateMe } from '../../api/auth'
import { updateProfile, importCv, createSectionItem } from '../../api/profile'
import { createSearch, activateSearch } from '../../api/searches'
import { ApiError } from '../../api/client'
import { formatApiErrorDetail } from '../../utils/apiErrors'
import ListSectionEditor, { emptyRow } from '../../components/ListSectionEditor'
import ExperienceGroupEditor from '../../components/ExperienceGroupEditor'
import EducationListEditor, { emptyEducationRow } from '../../components/EducationListEditor'
import CityAutocomplete from '../../components/CityAutocomplete'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

const SECTION_KEYS = ['skills', 'certifications', 'languages']

let nextGroupKey = 0
function makeGroupKey() {
  nextGroupKey += 1
  return `group-${nextGroupKey}`
}

function importedListToRows(items, fields) {
  return (items || []).map((item) => {
    const row = emptyRow(fields)
    for (const field of fields) {
      row[field.name] = item[field.name] ?? ''
    }
    return row
  })
}

function importedEducationsToRows(items) {
  // Il parsing del CV importato non estrae città/paese strutturati né
  // sa se un'istruzione è ancora in corso: pre-popola solo i campi
  // testuali di base, il resto resta da compilare manualmente.
  return (items || []).map((item) => ({
    ...emptyEducationRow(),
    institution: item.institution || '',
    title: item.title || '',
    location: item.location || '',
    notes: item.notes || '',
  }))
}

function groupExperiencesByCompany(items) {
  const groups = []
  const byName = new Map()
  for (const item of items || []) {
    const companyName = item.company || ''
    let group = byName.get(companyName)
    if (!group) {
      group = { _key: makeGroupKey(), company: companyName, roles: [] }
      byName.set(companyName, group)
      groups.push(group)
    }
    group.roles.push({
      _key: makeGroupKey(),
      role: item.role || '',
      location: item.location || '',
      bullets: item.bullets || [],
    })
  }
  return groups
}

export default function OnboardingPage() {
  const { t } = useLanguage()
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [preferences, setPreferences] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    objective_statement: user?.objective_statement || '',
    cv_language_mode: user?.cv_language_mode || 'job_language',
    cv_include_photo: user?.cv_include_photo || false,
  })

  const [profileFields, setProfileFields] = useState({
    summary: '',
    phone: '',
    city: '',
    country_code: '',
    linkedin_url: '',
  })
  const [profileCountry, setProfileCountry] = useState('')
  const [photoFile, setPhotoFile] = useState(null)
  const [cvNotice, setCvNotice] = useState('')

  const SKILL_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const CERTIFICATION_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const LANGUAGE_FIELDS = [
    { name: 'language', label: t('onboarding.language') },
    { name: 'level', label: t('onboarding.level') },
  ]

  const SECTION_CONFIG = {
    skills: { fields: SKILL_FIELDS, title: t('onboarding.skills'), addLabel: t('onboarding.addSkill') },
    certifications: { fields: CERTIFICATION_FIELDS, title: t('onboarding.certifications'), addLabel: t('onboarding.addCertification') },
    languages: { fields: LANGUAGE_FIELDS, title: t('onboarding.languages'), addLabel: t('onboarding.addLanguage') },
  }

  const [companies, setCompanies] = useState([])
  const [educations, setEducations] = useState([])
  const [sections, setSections] = useState({
    skills: [],
    certifications: [],
    languages: [],
  })

  const [search, setSearch] = useState({ keywords: '', city: '', country: '' })

  async function handlePreferencesSubmit(event) {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      await updateMe(preferences)
      await refreshUser()
      setStep(2)
    } catch {
      setError(t('common.genericError'))
    } finally {
      setSaving(false)
    }
  }

  async function handleCvUpload(event) {
    const file = event.target.files[0]
    if (!file) return
    setError('')
    setCvNotice('')
    setSaving(true)
    try {
      const structured = await importCv(file)
      setProfileFields({
        summary: structured.summary || '',
        phone: '',
        city: '',
        country_code: '',
        linkedin_url: '',
      })
      setProfileCountry('')
      setCompanies(groupExperiencesByCompany(structured.experiences))
      setEducations(importedEducationsToRows(structured.educations))
      setSections({
        skills: importedListToRows(structured.skills, SKILL_FIELDS),
        certifications: importedListToRows(structured.certifications, CERTIFICATION_FIELDS),
        languages: importedListToRows(structured.languages, LANGUAGE_FIELDS),
      })
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setCvNotice(t('onboarding.uploadCvUnreadable'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setSaving(false)
    }
  }

  // Le righe non ancora inviate al server hanno `_key` stringa (generata
  // localmente da `makeKey`/`makeGroupKey`); dopo la creazione riuscita
  // viene sostituita con l'id numerico reale. Se un tentativo di
  // salvataggio fallisce a metà (es. errore sulle sezioni successive) e
  // l'utente clicca di nuovo "Salva profilo", questo evita di recreare —
  // duplicando — le righe già create con successo nel tentativo precedente.
  function isCreatedRow(row) {
    return typeof row._key === 'number'
  }

  async function handleProfileSubmit(event) {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      if (photoFile) {
        const formData = new FormData()
        Object.entries(profileFields).forEach(([key, value]) => formData.append(key, value))
        formData.append('photo', photoFile)
        await updateProfile(formData, { isMultipart: true })
      } else {
        await updateProfile(profileFields)
      }

      const nextCompanies = []
      for (const companyGroup of companies) {
        const nextRoles = []
        for (const role of companyGroup.roles) {
          if (isCreatedRow(role)) {
            nextRoles.push(role)
            continue
          }
          const created = await createSectionItem('experiences', {
            company: companyGroup.company,
            role: role.role,
            location: role.location,
            location_country_code: role.location_country_code,
            start_date: role.start_date || null,
            end_date: role.ongoing ? null : role.end_date || null,
            bullets: role.bullets,
          })
          nextRoles.push({ ...role, _key: created.id })
        }
        nextCompanies.push({ ...companyGroup, roles: nextRoles })
      }
      setCompanies(nextCompanies)

      const nextEducations = []
      for (const edu of educations) {
        if (isCreatedRow(edu)) {
          nextEducations.push(edu)
          continue
        }
        const { _key, ongoing, ...payload } = edu
        const created = await createSectionItem('educations', {
          ...payload,
          start_date: payload.start_date || null,
          end_date: ongoing ? null : payload.end_date || null,
        })
        nextEducations.push({ ...edu, _key: created.id })
      }
      setEducations(nextEducations)

      const nextSections = { ...sections }
      for (const sectionKey of SECTION_KEYS) {
        const nextRows = []
        for (const row of sections[sectionKey]) {
          if (isCreatedRow(row)) {
            nextRows.push(row)
            continue
          }
          const { _key, ...payload } = row
          const created = await createSectionItem(sectionKey, payload)
          nextRows.push({ ...row, _key: created.id })
        }
        nextSections[sectionKey] = nextRows
      }
      setSections(nextSections)

      setStep(3)
    } catch (err) {
      const detail = formatApiErrorDetail(err)
      setError(detail ? `${t('common.genericError')} (${detail})` : t('common.genericError'))
    } finally {
      setSaving(false)
    }
  }

  async function handleSearchSubmit(event) {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      const created = await createSearch(search)
      await activateSearch(created.id)
      navigate('/list')
    } catch {
      setError(t('common.genericError'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-balance">{t('onboarding.title')}</h1>
        <ol className="mt-4 flex gap-5 border-b border-border pb-4 text-sm font-medium text-muted-foreground">
          {[
            ['stepPreferences', 1],
            ['stepProfile', 2],
            ['stepSearch', 3],
          ].map(([key, n]) => (
            <li
              key={key}
              aria-current={step === n ? 'step' : undefined}
              className={
                step === n
                  ? 'relative pb-3 text-foreground after:absolute after:bottom-[-1px] after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-primary'
                  : ''
              }
            >
              {t(`onboarding.${key}`)}
            </li>
          ))}
        </ol>
      </div>

      {error && (
        <p role="alert" className="rounded-md bg-destructive-soft px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {step === 1 && (
        <Card>
          <form onSubmit={handlePreferencesSubmit}>
            <CardContent className="flex flex-col gap-5 pt-6">
              <div className="flex flex-wrap gap-5">
                <div className="flex min-w-40 flex-1 flex-col gap-1.5">
                  <Label htmlFor="first-name">{t('onboarding.firstName')}</Label>
                  <Input
                    id="first-name"
                    type="text"
                    required
                    value={preferences.first_name}
                    onChange={(event) =>
                      setPreferences({ ...preferences, first_name: event.target.value })
                    }
                  />
                </div>
                <div className="flex min-w-40 flex-1 flex-col gap-1.5">
                  <Label htmlFor="last-name">{t('onboarding.lastName')}</Label>
                  <Input
                    id="last-name"
                    type="text"
                    required
                    value={preferences.last_name}
                    onChange={(event) =>
                      setPreferences({ ...preferences, last_name: event.target.value })
                    }
                  />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="objective">{t('onboarding.objectiveLabel')}</Label>
                <Textarea
                  id="objective"
                  placeholder={t('onboarding.objectivePlaceholder')}
                  value={preferences.objective_statement}
                  onChange={(event) =>
                    setPreferences({ ...preferences, objective_statement: event.target.value })
                  }
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cv-template">{t('onboarding.cvTemplateLabel')}</Label>
                <Input id="cv-template" value={t('onboarding.cvTemplateValue')} disabled readOnly />
              </div>
              <fieldset className="flex flex-col gap-2.5">
                <legend className="mb-1 text-sm font-medium text-foreground">
                  {t('onboarding.cvLanguageLabel')}
                </legend>
                <RadioGroup
                  value={preferences.cv_language_mode}
                  onValueChange={(value) => setPreferences({ ...preferences, cv_language_mode: value })}
                >
                  <label className="flex items-center gap-2.5 text-sm">
                    <RadioGroupItem value="job_language" />
                    {t('onboarding.cvLanguageJob')}
                  </label>
                  <label className="flex items-center gap-2.5 text-sm">
                    <RadioGroupItem value="english" />
                    {t('onboarding.cvLanguageEnglish')}
                  </label>
                </RadioGroup>
              </fieldset>
              <label className="flex items-center gap-2.5 text-sm">
                <Checkbox
                  checked={preferences.cv_include_photo}
                  onCheckedChange={(checked) =>
                    setPreferences({ ...preferences, cv_include_photo: checked === true })
                  }
                />
                {t('onboarding.cvIncludePhotoLabel')}
              </label>
            </CardContent>
            <CardFooter>
              <Button type="submit" disabled={saving}>
                {t('onboarding.next')}
              </Button>
            </CardFooter>
          </form>
        </Card>
      )}

      {step === 2 && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>{t('onboarding.uploadCvTitle')}</CardTitle>
              <CardDescription>{t('onboarding.uploadCvHint')}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Input type="file" accept=".pdf,.docx" onChange={handleCvUpload} disabled={saving} />
              {cvNotice && (
                <p role="status" className="text-sm text-muted-foreground">
                  {cvNotice}
                </p>
              )}
            </CardContent>
          </Card>

          <form onSubmit={handleProfileSubmit} className="flex flex-col gap-6">
            <Card>
              <CardContent className="flex flex-col gap-5 pt-6">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="summary">{t('onboarding.profileSummary')}</Label>
                  <Textarea
                    id="summary"
                    value={profileFields.summary}
                    onChange={(event) => setProfileFields({ ...profileFields, summary: event.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="phone">{t('onboarding.profilePhone')}</Label>
                  <Input
                    id="phone"
                    type="text"
                    placeholder={t('onboarding.profilePhonePlaceholder')}
                    value={profileFields.phone}
                    onChange={(event) => setProfileFields({ ...profileFields, phone: event.target.value })}
                  />
                </div>
                <CityAutocomplete
                  cityId="city"
                  countryId="country"
                  city={profileFields.city}
                  country={profileCountry}
                  onChange={({ city, country, countryCode }) => {
                    setProfileFields({
                      ...profileFields,
                      city,
                      country_code: countryCode ?? profileFields.country_code,
                    })
                    setProfileCountry(country)
                  }}
                />
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="linkedin">{t('onboarding.profileLinkedin')}</Label>
                  <Input
                    id="linkedin"
                    type="text"
                    value={profileFields.linkedin_url}
                    onChange={(event) =>
                      setProfileFields({ ...profileFields, linkedin_url: event.target.value })
                    }
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="photo">{t('onboarding.profilePhoto')}</Label>
                  <Input
                    id="photo"
                    type="file"
                    accept="image/*"
                    onChange={(event) => setPhotoFile(event.target.files[0] || null)}
                  />
                </div>
              </CardContent>
            </Card>

            <ExperienceGroupEditor companies={companies} onChange={setCompanies} t={t} />
            {companies.reduce((total, group) => total + group.roles.length, 0) > 5 && (
              <p role="status" className="text-sm text-muted-foreground">
                {t('onboarding.experiencesLimitWarning')}
              </p>
            )}

            <EducationListEditor rows={educations} onChange={setEducations} t={t} />

            {SECTION_KEYS.map((sectionKey) => (
              <ListSectionEditor
                key={sectionKey}
                title={SECTION_CONFIG[sectionKey].title}
                addLabel={SECTION_CONFIG[sectionKey].addLabel}
                removeLabel={t('onboarding.remove')}
                fields={SECTION_CONFIG[sectionKey].fields}
                rows={sections[sectionKey]}
                onChange={(rows) => setSections({ ...sections, [sectionKey]: rows })}
              />
            ))}

            <Button type="submit" disabled={saving} className="w-fit">
              {t('onboarding.saveProfile')}
            </Button>
          </form>
        </>
      )}

      {step === 3 && (
        <Card>
          <form onSubmit={handleSearchSubmit}>
            <CardHeader>
              <CardTitle>{t('onboarding.firstSearchTitle')}</CardTitle>
              <CardDescription>{t('onboarding.firstSearchHint')}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="search-keywords">{t('onboarding.searchKeywords')}</Label>
                <Input
                  id="search-keywords"
                  type="text"
                  value={search.keywords}
                  onChange={(event) => setSearch({ ...search, keywords: event.target.value })}
                  required
                />
              </div>
              <CityAutocomplete
                cityId="search-city"
                countryId="search-country"
                city={search.city}
                country={search.country}
                onChange={({ city, country }) => setSearch({ ...search, city, country })}
              />
            </CardContent>
            <CardFooter>
              <Button type="submit" disabled={saving}>
                {t('onboarding.finish')}
              </Button>
            </CardFooter>
          </form>
        </Card>
      )}
    </div>
  )
}
