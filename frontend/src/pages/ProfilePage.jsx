import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { updateMe } from '../api/auth'
import {
  fetchProfile,
  updateProfile,
  createSectionItem,
  updateSectionItem,
  deleteSectionItem,
  removeProfilePhoto,
} from '../api/profile'
import { Info, Link2, Trash2, Upload } from 'lucide-react'
import ListSectionEditor, { emptyRow } from '../components/ListSectionEditor'
import { getLanguageLevelOptions, getLanguageNameOptions } from '../utils/languageOptions'
import ExperienceGroupEditor from '../components/ExperienceGroupEditor'
import EducationListEditor from '../components/EducationListEditor'
import CityAutocomplete from '../components/CityAutocomplete'
import { formatApiErrorDetail } from '../utils/apiErrors'
import { useToast } from '@/components/ToastProvider'
import { AccordionSection } from '@/components/ui/accordion'
import { ActionBar } from '@/components/ui/action-bar'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Modal, ModalActions, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'

const SECTION_KEYS = ['skills', 'certifications', 'languages']

let nextGroupKey = 0
function makeGroupKey() {
  nextGroupKey += 1
  return `group-${nextGroupKey}`
}

// A differenza dell'onboarding (che parte sempre da zero), qui ogni riga
// riflette una risorsa già esistente sul server: `_key` è l'id reale
// quando presente, così in salvataggio sappiamo se fare PATCH (riga
// esistente) o POST (riga aggiunta in questa sessione di modifica).
function existingListToRows(items, fields) {
  return (items || []).map((item) => {
    const row = emptyRow(fields)
    row._key = item.id
    for (const field of fields) {
      row[field.name] = item[field.name] ?? ''
    }
    return row
  })
}

function existingEducationsToRows(items) {
  return (items || []).map((item) => ({
    _key: item.id,
    institution: item.institution || '',
    title: item.title || '',
    location: item.location || '',
    location_country_code: item.location_country_code || '',
    start_date: item.start_date || '',
    end_date: item.end_date || '',
    ongoing: !item.end_date,
    notes: item.notes || '',
  }))
}

function flattenEducations(rows) {
  return rows.map((row) => {
    const { _key, ongoing, ...payload } = row
    return {
      _key,
      ...payload,
      start_date: payload.start_date || null,
      end_date: ongoing ? null : payload.end_date || null,
    }
  })
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
      _key: item.id,
      role: item.role || '',
      location: item.location || '',
      location_country_code: item.location_country_code || '',
      start_date: item.start_date || '',
      end_date: item.end_date || '',
      ongoing: !item.end_date,
      bullets: item.bullets || [],
      technologies: item.technologies || [],
    })
  }
  return groups
}

function flattenRoles(companies) {
  return companies.flatMap((group) =>
    group.roles.map((role) => ({
      _key: role._key,
      company: group.company,
      role: role.role,
      location: role.location,
      location_country_code: role.location_country_code,
      start_date: role.start_date || null,
      end_date: role.ongoing ? null : role.end_date || null,
      bullets: role.bullets,
      technologies: role.technologies || [],
    })),
  )
}

// Le righe con `_key` numerico esistevano già sul server (id reale); quelle
// con `_key` stringa (`group-N`/`row-N`, generate localmente) sono nuove.
function isExistingRow(row) {
  return typeof row._key === 'number'
}

// Riporta gli id reali di `savedRoles` (stesso ordine di `flattenRoles`,
// azienda per azienda) dentro la struttura raggruppata per azienda usata
// da `ExperienceGroupEditor`, senza toccare il raggruppamento in sé.
function regroupSavedRoles(companies, savedRoles) {
  let index = 0
  return companies.map((group) => ({
    ...group,
    roles: group.roles.map((role) => ({ ...role, _key: savedRoles[index++]._key })),
  }))
}

// Ritorna le righe salvate con l'id reale del server al posto di ogni
// `_key` locale (stringa) appena creato: senza, un salvataggio ripetuto
// (es. dopo un errore su una sezione successiva) non riconosce più le
// righe già create in questa sessione come "esistenti" e le rimanda come
// nuove, duplicandole sul server.
// Sprint 81: istantanea del contenuto modificabile, senza le chiavi interne
// (`_key` cambia da locale a id reale dopo il salvataggio senza che il
// contenuto cambi). Serve a mostrare "Salva modifiche" solo con modifiche.
function contentSnapshot(value) {
  return JSON.stringify(value, (key, item) => (key === '_key' ? undefined : item))
}

async function saveSection(section, currentRows, initialIds) {
  const currentIds = new Set(currentRows.filter(isExistingRow).map((row) => row._key))
  for (const id of initialIds) {
    if (!currentIds.has(id)) {
      await deleteSectionItem(section, id)
    }
  }
  const savedRows = []
  for (const row of currentRows) {
    const { _key, ...payload } = row
    if (isExistingRow(row)) {
      await updateSectionItem(section, _key, payload)
      savedRows.push(row)
    } else {
      const created = await createSectionItem(section, payload)
      savedRows.push({ ...row, _key: created.id })
    }
  }
  return savedRows
}

export default function ProfilePage() {
  const { t, lang } = useLanguage()
  const { user, refreshUser } = useAuth()
  const { showToast } = useToast()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  // Nome e obiettivo stanno sull'account (PATCH /api/accounts/me/);
  // l'obiettivo è modificabile anche dopo l'onboarding (Sprint 70).
  const [nameFields, setNameFields] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    objective_statement: user?.objective_statement || '',
  })
  const [removingPhoto, setRemovingPhoto] = useState(false)
  const [confirmPhotoRemoval, setConfirmPhotoRemoval] = useState(false)
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
  // URL firmato a scadenza (Sprint 66), mai il path /media/ del file.
  const [photoUrl, setPhotoUrl] = useState(null)
  const [companies, setCompanies] = useState([])
  const [initialExperienceIds, setInitialExperienceIds] = useState([])
  const [educations, setEducations] = useState([])
  const [initialEducationIds, setInitialEducationIds] = useState([])
  const [sections, setSections] = useState({
    skills: [],
    certifications: [],
    languages: [],
  })
  const [initialSectionIds, setInitialSectionIds] = useState({
    skills: [],
    certifications: [],
    languages: [],
  })
  // Contenuto all'ultimo caricamento o salvataggio riuscito (Sprint 81).
  const [baseline, setBaseline] = useState(null)
  const [needsBaseline, setNeedsBaseline] = useState(false)
  const snapshot = useMemo(
    () =>
      contentSnapshot({
        nameFields,
        profileFields,
        companies,
        educations,
        sections,
        photo: photoFile ? photoFile.name : null,
      }),
    [nameFields, profileFields, companies, educations, sections, photoFile],
  )
  useEffect(() => {
    if (needsBaseline) {
      setBaseline(snapshot)
      setNeedsBaseline(false)
    }
  }, [needsBaseline, snapshot])
  const dirty = baseline != null && snapshot !== baseline

  const SKILL_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const CERTIFICATION_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const LANGUAGE_FIELDS = [
    { name: 'language', label: t('onboarding.language'), options: getLanguageNameOptions(lang) },
    { name: 'level', label: t('onboarding.level'), options: getLanguageLevelOptions(lang) },
  ]

  const SECTION_CONFIG = {
    skills: { fields: SKILL_FIELDS, title: t('profile.skills'), addLabel: t('profile.addSkill') },
    certifications: {
      fields: CERTIFICATION_FIELDS,
      title: t('profile.certifications'),
      addLabel: t('profile.addCertification'),
    },
    languages: { fields: LANGUAGE_FIELDS, title: t('profile.languages'), addLabel: t('profile.addLanguage') },
  }

  // Applica un profilo scaricato dal server allo stato del form, al
  // caricamento iniziale della pagina.
  function applyProfileData(data) {
    setProfileFields({
      summary: data.summary || '',
      phone: data.phone || '',
      email: data.email || '',
      city: data.city || '',
      country_code: data.country_code || '',
      linkedin_url: data.linkedin_url || '',
    })
    setProfileCountry(data.country_code || '')
    setPhotoUrl(data.photo_url || null)
    setCompanies(groupExperiencesByCompany(data.experiences))
    setInitialExperienceIds((data.experiences || []).map((exp) => exp.id))
    setEducations(existingEducationsToRows(data.educations))
    setInitialEducationIds((data.educations || []).map((item) => item.id))
    setSections({
      skills: existingListToRows(data.skills, SKILL_FIELDS),
      certifications: existingListToRows(data.certifications, CERTIFICATION_FIELDS),
      languages: existingListToRows(data.languages, LANGUAGE_FIELDS),
    })
    setInitialSectionIds({
      skills: (data.skills || []).map((item) => item.id),
      certifications: (data.certifications || []).map((item) => item.id),
      languages: (data.languages || []).map((item) => item.id),
    })
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetchProfile()
      .then((data) => {
        if (!cancelled) {
          applyProfileData(data)
          setNeedsBaseline(true)
        }
      })
      .catch(() => {
        if (!cancelled) setError(t('profile.loadError'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setSaving(true)
    try {
      await updateMe(nameFields)
      await refreshUser()

      if (photoFile) {
        const formData = new FormData()
        Object.entries(profileFields).forEach(([key, value]) => formData.append(key, value))
        formData.append('photo', photoFile)
        const saved = await updateProfile(formData, { isMultipart: true })
        setPhotoUrl(saved.photo_url || null)
      } else {
        await updateProfile(profileFields)
      }

      const savedRoles = await saveSection('experiences', flattenRoles(companies), initialExperienceIds)
      const savedExperienceIds = savedRoles.map((role) => role._key)
      setCompanies(regroupSavedRoles(companies, savedRoles))
      setInitialExperienceIds(savedExperienceIds)

      const savedEducations = await saveSection('educations', flattenEducations(educations), initialEducationIds)
      setEducations(savedEducations)
      setInitialEducationIds(savedEducations.map((row) => row._key))

      for (const sectionKey of SECTION_KEYS) {
        const savedRows = await saveSection(sectionKey, sections[sectionKey], initialSectionIds[sectionKey])
        setSections((prev) => ({ ...prev, [sectionKey]: savedRows }))
        setInitialSectionIds((prev) => ({ ...prev, [sectionKey]: savedRows.map((row) => row._key) }))
      }

      setNotice(t('profile.saved'))
      // La barra "Salva modifiche" è in fondo (e sparisce): l'esito anche come avviso.
      showToast(t('profile.saved'))
      setPhotoFile(null)
      setNeedsBaseline(true)
      // Aggiorna `profile_status` (banner del profilo incompleto).
      refreshUser().catch(() => {})
    } catch (err) {
      const detail = formatApiErrorDetail(err)
      const message = detail ? `${t('profile.saveError')} (${detail})` : t('profile.saveError')
      setError(message)
      showToast(message)
    } finally {
      setSaving(false)
    }
  }

  // Sprint 78: conferma in una finestra dell'app (prima `window.confirm`).
  async function handleRemovePhoto() {
    setConfirmPhotoRemoval(false)
    setError('')
    setNotice('')
    setRemovingPhoto(true)
    try {
      await removeProfilePhoto()
      setPhotoUrl(null)
      setNotice(t('profileExtras.photoRemoved'))
    } catch {
      setError(t('common.genericError'))
    } finally {
      setRemovingPhoto(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center pt-16">
        <Spinner size={28} />
      </div>
    )
  }

  const fullName = [nameFields.first_name, nameFields.last_name].filter(Boolean).join(' ')
  const initials =
    [nameFields.first_name, nameFields.last_name]
      .map((part) => part.trim()[0] || '')
      .join('')
      .toUpperCase() || '?'
  const roleCount = companies.reduce((total, group) => total + group.roles.length, 0)
  const count = (n, oneKey, manyKey) => (n === 0 ? '' : n === 1 ? t(oneKey) : t(manyKey).replace('{count}', n))
  // I titoli interni degli editor condivisi (legend) restano per gli screen
  // reader: il titolo visibile è quello della fisarmonica.
  const editorWrapper = '[&>fieldset>legend]:sr-only'

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 pb-6 pt-5 lg:pt-8">
      <h1 className="text-[28px] font-bold leading-tight tracking-[-0.01em] text-foreground">{t('profile.title')}</h1>
      <div className="flex items-center gap-3.5">
        {photoUrl ? (
          <img src={photoUrl} alt="" className="h-14 w-14 shrink-0 rounded-full border border-border object-cover" />
        ) : (
          <span aria-hidden="true" className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary-soft text-lg font-bold text-primary">
            {initials}
          </span>
        )}
        <div className="min-w-0">
          <p className="break-words text-xl font-bold leading-tight text-foreground">{fullName || user?.email}</p>
          <p className="text-sm text-muted-foreground">{t('profileExtras.masterSubtitle')}</p>
        </div>
      </div>

      {error && <Banner variant="error">{error}</Banner>}
      {notice && (
        <Banner variant="success" role="status">
          {notice}
        </Banner>
      )}

      <form id="profile-form" onSubmit={handleSubmit} className="flex flex-col gap-3">
        <AccordionSection title={t('profileExtras.contactSection')} defaultOpen keepMounted data-testid="profile-contact">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('onboarding.firstName')}>
              <Input
                id="first-name"
                type="text"
                required
                value={nameFields.first_name}
                onChange={(event) => setNameFields({ ...nameFields, first_name: event.target.value })}
              />
            </Field>
            <Field label={t('onboarding.lastName')}>
              <Input
                id="last-name"
                type="text"
                required
                value={nameFields.last_name}
                onChange={(event) => setNameFields({ ...nameFields, last_name: event.target.value })}
              />
            </Field>
          </div>
          <Field label={t('profile.phone')}>
            <Input
              id="phone"
              type="text"
              placeholder={t('onboarding.profilePhonePlaceholder')}
              value={profileFields.phone}
              onChange={(event) => setProfileFields({ ...profileFields, phone: event.target.value })}
            />
          </Field>
          <Field label={t('profile.email')}>
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
          <div className="flex flex-col gap-1.5">
            <label htmlFor="linkedin" className="text-[13px] font-semibold leading-snug text-label">
              {t('profile.linkedin')}
            </label>
            <div className="relative">
              <Link2 className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                id="linkedin"
                type="text"
                className="pl-11"
                placeholder="https://www.linkedin.com/in/..."
                value={profileFields.linkedin_url}
                onChange={(event) => setProfileFields({ ...profileFields, linkedin_url: event.target.value })}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              {photoUrl ? (
                <img src={photoUrl} alt={t('profile.photo')} className="h-14 w-14 rounded-full border border-border object-cover" />
              ) : (
                <span aria-hidden="true" className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-soft font-bold text-primary">
                  {initials}
                </span>
              )}
              <span className="min-w-0 flex-1 text-[15px] font-semibold text-foreground">{t('profile.photo')}</span>
              <label
                htmlFor="photo"
                className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-button border border-input bg-card px-4 text-[15px] font-semibold text-primary hover:bg-tint has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/30"
              >
                <Upload className="h-4 w-4" aria-hidden="true" />
                {t('profileExtras.photoUpload')}
                <input
                  id="photo"
                  type="file"
                  className="sr-only"
                  accept="image/jpeg,image/png,image/webp"
                  aria-label={t('profile.photo')}
                  onChange={(event) => setPhotoFile(event.target.files[0] || null)}
                />
              </label>
              {photoUrl ? (
                <Button
                  type="button"
                  variant="text"
                  onClick={() => setConfirmPhotoRemoval(true)}
                  disabled={removingPhoto || saving}
                  className="text-destructive-text"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  {t('profileExtras.photoRemove')}
                </Button>
              ) : null}
            </div>
            {photoFile ? (
              <p className="text-[13px] text-muted-foreground">
                <span className="font-semibold text-foreground">{photoFile.name}</span> · {t('profileExtras.photoNewHint')}
              </p>
            ) : null}
          </div>
        </AccordionSection>

        <AccordionSection title={t('profileExtras.objectiveSection')} keepMounted>
          <Field label={t('onboarding.objectiveLabel')} hint={t('profileExtras.objectiveHint')}>
            <Textarea
              id="objective"
              maxLength={2000}
              placeholder={t('onboarding.objectivePlaceholder')}
              value={nameFields.objective_statement}
              onChange={(event) => setNameFields({ ...nameFields, objective_statement: event.target.value })}
            />
          </Field>
        </AccordionSection>

        <AccordionSection title={t('profile.summary')} keepMounted>
          <Field label={t('profile.summary')}>
            <Textarea
              id="summary"
              className="min-h-32"
              value={profileFields.summary}
              onChange={(event) => setProfileFields({ ...profileFields, summary: event.target.value })}
            />
          </Field>
        </AccordionSection>

        <AccordionSection
          title={t('profile.experiences')}
          summary={count(companies.length, 'profileExtras.companiesOne', 'profileExtras.companiesMany')}
          keepMounted
          data-testid="profile-experiences"
        >
          {roleCount > 5 ? (
            <Banner variant="note" icon={Info}>
              {t('profile.experiencesLimitWarning')}
            </Banner>
          ) : null}
          <div className={editorWrapper}>
            <ExperienceGroupEditor
              companies={companies}
              onChange={setCompanies}
              t={t}
              titleKey="profile.experiences"
              hintKey="profile.experiencesHint"
            />
          </div>
        </AccordionSection>

        <AccordionSection
          title={t('profile.educations')}
          summary={count(educations.length, 'profileExtras.degreesOne', 'profileExtras.degreesMany')}
          keepMounted
        >
          <div className={editorWrapper}>
            <EducationListEditor rows={educations} onChange={setEducations} t={t} />
          </div>
        </AccordionSection>

        {SECTION_KEYS.map((sectionKey) => (
          <AccordionSection
            key={sectionKey}
            title={SECTION_CONFIG[sectionKey].title}
            summary={sections[sectionKey].length ? String(sections[sectionKey].length) : ''}
            keepMounted
          >
            <div className={editorWrapper}>
              <ListSectionEditor
                title={SECTION_CONFIG[sectionKey].title}
                addLabel={SECTION_CONFIG[sectionKey].addLabel}
                removeLabel={t('profile.remove')}
                fields={SECTION_CONFIG[sectionKey].fields}
                rows={sections[sectionKey]}
                onChange={(rows) => setSections({ ...sections, [sectionKey]: rows })}
              />
            </div>
          </AccordionSection>
        ))}
      </form>

      {/* Sprint 81: sopra la barra di tab (che resta visibile, mockup
          `profilo`) e solo con modifiche non salvate o un errore da
          correggere; durante il salvataggio resta visibile. */}
      {dirty || saving || error ? (
        <ActionBar stacked>
          <Button type="submit" form="profile-form" size="lg" disabled={saving}>
            {saving ? t('profileExtras.saving') : t('profile.save')}
          </Button>
        </ActionBar>
      ) : null}

      <Modal open={confirmPhotoRemoval} onOpenChange={setConfirmPhotoRemoval}>
        <ModalContent>
          <ModalTitle>{t('profileExtras.photoRemoveTitle')}</ModalTitle>
          <ModalDescription className="text-[15px]">{t('profileExtras.photoRemoveConfirm')}</ModalDescription>
          <ModalActions>
            <Button variant="destructive" size="lg" onClick={handleRemovePhoto} disabled={removingPhoto}>
              {t('profileExtras.photoRemove')}
            </Button>
            <Button variant="text" onClick={() => setConfirmPhotoRemoval(false)}>
              {t('common.cancel')}
            </Button>
          </ModalActions>
        </ModalContent>
      </Modal>
    </div>
  )
}
