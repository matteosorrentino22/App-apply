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
import TimezoneSelect from '../../components/TimezoneSelect'
import { browserTimeZone } from '../../utils/date'
import { getLanguageLevelOptions, getLanguageNameOptions } from '../../utils/languageOptions'
import ExperienceGroupEditor from '../../components/ExperienceGroupEditor'
import EducationListEditor, { emptyEducationRow } from '../../components/EducationListEditor'
import CityAutocomplete from '../../components/CityAutocomplete'
import CityChipsField from '../../components/CityChipsField'
import { AlertTriangle, Info, Upload } from 'lucide-react'
import { ActionBar } from '@/components/ui/action-bar'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { SegmentedControl } from '@/components/ui/segmented'
import { cn } from '@/lib/utils'

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
      technologies: item.technologies || [],
    })
  }
  return groups
}

// Fuso proposto (Sprint 70): quello dell'account, salvo che sia ancora il
// default del server (Europe/Rome, cioè probabilmente mai scelto) e il
// dispositivo sia altrove: in quel caso il fuso del dispositivo.
const SERVER_DEFAULT_TIME_ZONE = 'Europe/Rome'

function initialTimeZone(user) {
  const saved = user?.timezone
  if (saved && saved !== SERVER_DEFAULT_TIME_ZONE) return saved
  return browserTimeZone() || saved || SERVER_DEFAULT_TIME_ZONE
}

// Errori dell'import CV con un messaggio dedicato (Sprint 70): il backend
// risponde con un `code` stabile (apps/profiles/views.py).
const CV_IMPORT_ERROR_CODES = [
  'file_missing',
  'file_too_large',
  'unsupported_type',
  'too_many_pages',
  'quota_exceeded',
  'ai_unavailable',
]
const MAX_CV_UPLOAD_BYTES = 5 * 1024 * 1024

function cvImportErrorKey(err) {
  if (!(err instanceof ApiError)) return 'common.genericError'
  if (err.status === 422) return 'onboarding.uploadCvUnreadable'
  if (err.status === 429) return 'common.tooManyRequests'
  // 413: corpo rifiutato da Caddy prima di arrivare al backend.
  if (err.status === 413) return 'cvImport.file_too_large'
  const code = err.data?.code
  if (CV_IMPORT_ERROR_CODES.includes(code)) return `cvImport.${code}`
  if (err.status === 502) return 'cvImport.ai_unavailable'
  return 'common.genericError'
}

export default function OnboardingPage() {
  const { t, lang } = useLanguage()
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
    timezone: initialTimeZone(user),
  })

  const [profileFields, setProfileFields] = useState({
    summary: '',
    phone: '',
    email: '',
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
    { name: 'language', label: t('onboarding.language'), options: getLanguageNameOptions(lang) },
    { name: 'level', label: t('onboarding.level'), options: getLanguageLevelOptions(lang) },
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

  // Sprint 84: paese + città (una sola nell'onboarding, come sul Free).
  const [search, setSearch] = useState({ search_type: 'job_role', keywords: '', country: '', cities: [] })

  async function handlePreferencesSubmit(event) {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      await updateMe(preferences)
      await refreshUser()
      setStep(2)
    } catch (err) {
      // Es. un fuso del dispositivo che il server non riconosce: il campo
      // in errore è indicato, l'utente può sceglierne un altro.
      const detail = formatApiErrorDetail(err)
      setError(detail ? `${t('common.genericError')} (${detail})` : t('common.genericError'))
    } finally {
      setSaving(false)
    }
  }

  async function handleCvUpload(event) {
    const file = event.target.files[0]
    // Stesso file scelto di nuovo dopo un errore: il campo va svuotato perché
    // il browser segnali di nuovo la scelta (riprova, mockup `onboarding2-err`).
    event.target.value = ''
    if (!file) return
    setError('')
    setCvNotice('')
    // Stesso limite del server: si evita di caricare un file che verrebbe rifiutato.
    if (file.size > MAX_CV_UPLOAD_BYTES) {
      setCvNotice(t('cvImport.file_too_large'))
      return
    }
    setSaving(true)
    try {
      const structured = await importCv(file)
      setProfileFields({
        summary: structured.summary || '',
        phone: structured.phone || '',
        email: structured.email || '',
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
      setCvNotice(t(cvImportErrorKey(err)))
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
            technologies: role.technologies || [],
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

      refreshUser().catch(() => {})
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

  const steps = [
    ['stepPreferences', 1],
    ['stepProfile', 2],
    ['stepSearch', 3],
  ]
  const stepTitle = { 1: t('onboarding.preferencesTitle'), 2: t('onboarding.profileStepTitle'), 3: t('onboarding.firstSearchTitle') }[step]
  const cardClass = 'flex flex-col gap-4 rounded-card border border-border bg-card p-4 shadow-card'

  // Sprint 79 (mockup `onboarding1`, `onboarding2`, `onboarding2-err`,
  // `onboarding3`): stessi tre passi, stessi dati e stesse chiamate di
  // prima; indicatore dei passi a barre, pulsante del passo nella barra in
  // basso, errore dell'import del CV in un riquadro con la possibilità di
  // riprovare scegliendo di nuovo il file.
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-4 pb-6 pt-4 lg:pt-8">
      <ol className="grid grid-cols-3 gap-2.5" aria-label={t('onboarding.title')}>
        {steps.map(([key, n]) => (
          <li key={key} aria-current={step === n ? 'step' : undefined} className="flex flex-col gap-1.5">
            <span className={cn('h-1.5 rounded-full', n <= step ? 'bg-primary' : 'bg-secondary')} aria-hidden="true" />
            <span className={cn('text-sm', step === n ? 'font-bold text-foreground' : 'text-muted-foreground')}>{t(`onboarding.${key}`)}</span>
          </li>
        ))}
      </ol>
      <h1 className="text-[28px] font-bold leading-tight tracking-[-0.01em] text-foreground">{stepTitle}</h1>

      {error ? <Banner variant="error">{error}</Banner> : null}

      {step === 1 && (
        <form id="onboarding-step" onSubmit={handlePreferencesSubmit} className="flex flex-col gap-4">
          <Field label={t('onboarding.firstName')}>
            <Input
              id="first-name"
              type="text"
              required
              value={preferences.first_name}
              onChange={(event) => setPreferences({ ...preferences, first_name: event.target.value })}
            />
          </Field>
          <Field label={t('onboarding.lastName')}>
            <Input
              id="last-name"
              type="text"
              required
              value={preferences.last_name}
              onChange={(event) => setPreferences({ ...preferences, last_name: event.target.value })}
            />
          </Field>
          <Field label={t('onboarding.objectiveLabel')}>
            <Textarea
              id="objective"
              placeholder={t('onboarding.objectivePlaceholder')}
              value={preferences.objective_statement}
              onChange={(event) => setPreferences({ ...preferences, objective_statement: event.target.value })}
            />
          </Field>
          <Field label={t('timezone.label')} hint={t('timezone.hint')}>
            <TimezoneSelect
              id="onboarding-timezone"
              value={preferences.timezone}
              onChange={(value) => setPreferences({ ...preferences, timezone: value })}
            />
          </Field>
          <Field label={t('onboarding.cvTemplateLabel')}>
            <Input id="cv-template" value={t('onboarding.cvTemplateValue')} disabled readOnly className="bg-secondary" />
          </Field>
          <fieldset className="flex flex-col gap-2.5">
            <legend className="mb-1.5 text-[13px] font-semibold leading-snug text-label">{t('onboarding.cvLanguageLabel')}</legend>
            <RadioGroup
              value={preferences.cv_language_mode}
              onValueChange={(value) => setPreferences({ ...preferences, cv_language_mode: value })}
              className="flex flex-col gap-2.5"
            >
              {[
                ['job_language', t('onboarding.cvLanguageJob')],
                ['english', t('onboarding.cvLanguageEnglish')],
              ].map(([value, label]) => (
                <label
                  key={value}
                  className={cn(
                    'flex min-h-14 cursor-pointer items-center gap-3 rounded-field border px-4 py-3 text-base font-semibold',
                    preferences.cv_language_mode === value ? 'border-primary bg-tint' : 'border-input bg-card',
                  )}
                >
                  <RadioGroupItem value={value} />
                  {label}
                </label>
              ))}
            </RadioGroup>
          </fieldset>
          <label className="flex min-h-11 cursor-pointer items-center gap-3 text-base text-foreground">
            <Checkbox
              checked={preferences.cv_include_photo}
              onCheckedChange={(checked) => setPreferences({ ...preferences, cv_include_photo: checked === true })}
            />
            {t('onboarding.cvIncludePhotoLabel')}
          </label>
        </form>
      )}

      {step === 2 && (
        <>
          <section className={cardClass} aria-labelledby="cv-upload-title">
            <div className="flex items-center gap-3.5">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-field bg-primary-soft text-primary">
                <Upload className="h-6 w-6" aria-hidden="true" />
              </span>
              <div>
                <h2 id="cv-upload-title" className="text-[17px] font-bold text-foreground">
                  {t('onboarding.uploadCvTitle')}
                </h2>
                <p className="text-sm text-muted-foreground">{t('onboarding.optional')}</p>
              </div>
            </div>
            <p className="text-[15px] leading-normal text-muted-foreground">{t('onboarding.uploadCvHint')}</p>
            <label
              className={cn(
                'inline-flex min-h-[52px] cursor-pointer items-center justify-center gap-2 rounded-button bg-primary px-5 py-3 text-base font-bold text-primary-foreground hover:bg-primary/90 has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/30',
                saving && 'pointer-events-none opacity-45',
              )}
            >
              <Upload className="h-5 w-5" aria-hidden="true" />
              {saving ? t('onboarding.uploadingCv') : t('onboarding.uploadCvButton')}
              <input
                type="file"
                className="sr-only"
                accept=".pdf,.docx"
                aria-label={t('onboarding.uploadCvTitle')}
                onChange={handleCvUpload}
                disabled={saving}
              />
            </label>
          </section>
          {cvNotice ? (
            <Banner variant="error" icon={AlertTriangle} role="status">
              {cvNotice} {t('onboarding.uploadCvRetry')}
            </Banner>
          ) : null}
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="h-px flex-1 bg-border" />
            {t('onboarding.orFillBelow')}
            <span className="h-px flex-1 bg-border" />
          </div>

          <form id="onboarding-step" onSubmit={handleProfileSubmit} className="flex flex-col gap-4">
            <section className={cardClass}>
              <Field label={t('onboarding.profileSummary')}>
                <Textarea
                  id="summary"
                  value={profileFields.summary}
                  onChange={(event) => setProfileFields({ ...profileFields, summary: event.target.value })}
                />
              </Field>
              <Field label={t('onboarding.profilePhone')}>
                <Input
                  id="phone"
                  type="text"
                  placeholder={t('onboarding.profilePhonePlaceholder')}
                  value={profileFields.phone}
                  onChange={(event) => setProfileFields({ ...profileFields, phone: event.target.value })}
                />
              </Field>
              <Field label={t('onboarding.profileEmail')}>
                <Input
                  id="email"
                  type="email"
                  placeholder={t('onboarding.profileEmailPlaceholder')}
                  value={profileFields.email}
                  onChange={(event) => setProfileFields({ ...profileFields, email: event.target.value })}
                />
              </Field>
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
              <Field label={t('onboarding.profileLinkedin')}>
                <Input
                  id="linkedin"
                  type="text"
                  placeholder="https://www.linkedin.com/in/..."
                  value={profileFields.linkedin_url}
                  onChange={(event) => setProfileFields({ ...profileFields, linkedin_url: event.target.value })}
                />
              </Field>
              <Field label={t('onboarding.profilePhoto')}>
                <Input
                  id="photo"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="h-auto py-2.5 text-sm"
                  onChange={(event) => setPhotoFile(event.target.files[0] || null)}
                />
              </Field>
            </section>

            <section className={cardClass}>
              <ExperienceGroupEditor companies={companies} onChange={setCompanies} t={t} />
              {companies.reduce((total, group) => total + group.roles.length, 0) > 5 ? (
                <Banner variant="note" icon={Info} role="status">
                  {t('onboarding.experiencesLimitWarning')}
                </Banner>
              ) : null}
            </section>

            <section className={cardClass}>
              <EducationListEditor rows={educations} onChange={setEducations} t={t} />
            </section>

            {SECTION_KEYS.map((sectionKey) => (
              <section key={sectionKey} className={cardClass}>
                <ListSectionEditor
                  title={SECTION_CONFIG[sectionKey].title}
                  addLabel={SECTION_CONFIG[sectionKey].addLabel}
                  removeLabel={t('onboarding.remove')}
                  fields={SECTION_CONFIG[sectionKey].fields}
                  rows={sections[sectionKey]}
                  onChange={(rows) => setSections({ ...sections, [sectionKey]: rows })}
                />
              </section>
            ))}
          </form>
        </>
      )}

      {step === 3 && (
        <form id="onboarding-step" onSubmit={handleSearchSubmit} className="flex flex-col gap-4">
          <p className="text-[15px] leading-normal text-muted-foreground">{t('onboarding.firstSearchHint')}</p>
          <div className="flex flex-col gap-1.5">
            <p aria-hidden="true" className="text-[13px] font-semibold leading-snug text-label">
              {t('account.searchTypeLabel')}
            </p>
            <SegmentedControl
              name="onboarding-search-type"
              label={t('account.searchTypeLabel')}
              value={search.search_type}
              onChange={(value) => setSearch({ ...search, search_type: value })}
              options={[
                { value: 'job_role', label: t('account.searchType_job_role') },
                { value: 'company', label: t('account.searchType_company') },
              ]}
            />
          </div>
          <Field label={t('onboarding.searchKeywords')}>
            <Input
              id="search-keywords"
              type="text"
              placeholder={t('settings.keywordsPlaceholder')}
              value={search.keywords}
              onChange={(event) => setSearch({ ...search, keywords: event.target.value })}
              required
            />
          </Field>
          <CityChipsField
            idPrefix="onboarding-search"
            country={search.country}
            onCountryChange={(country) => setSearch({ ...search, country, cities: [] })}
            cities={search.cities}
            onCitiesChange={(cities) => setSearch({ ...search, cities })}
            maxCities={1}
            hint={t('searches.citiesHintFree')}
          />
        </form>
      )}

      <ActionBar>
        <Button type="submit" form="onboarding-step" size="lg" disabled={saving}>
          {step === 1 ? t('onboarding.next') : step === 2 ? t('onboarding.saveProfile') : t('onboarding.finish')}
        </Button>
      </ActionBar>
    </div>
  )
}
