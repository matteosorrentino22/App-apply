import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { updateMe } from '../api/auth'
import {
  fetchProfile,
  updateProfile,
  createSectionItem,
  updateSectionItem,
  deleteSectionItem,
} from '../api/profile'
import ListSectionEditor, { emptyRow } from '../components/ListSectionEditor'
import ExperienceGroupEditor from '../components/ExperienceGroupEditor'
import EducationListEditor from '../components/EducationListEditor'
import CityAutocomplete from '../components/CityAutocomplete'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'

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
    return { _key, ...payload, end_date: ongoing ? null : payload.end_date || null }
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
    })),
  )
}

// Le righe con `_key` numerico esistevano già sul server (id reale); quelle
// con `_key` stringa (`group-N`/`row-N`, generate localmente) sono nuove.
function isExistingRow(row) {
  return typeof row._key === 'number'
}

async function saveSection(section, currentRows, initialIds) {
  const currentIds = new Set(currentRows.filter(isExistingRow).map((row) => row._key))
  for (const id of initialIds) {
    if (!currentIds.has(id)) {
      await deleteSectionItem(section, id)
    }
  }
  for (const row of currentRows) {
    const { _key, ...payload } = row
    if (isExistingRow(row)) {
      await updateSectionItem(section, _key, payload)
    } else {
      await createSectionItem(section, payload)
    }
  }
}

export default function ProfilePage() {
  const { t } = useLanguage()
  const { user, refreshUser } = useAuth()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const [nameFields, setNameFields] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
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

  const SKILL_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const CERTIFICATION_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const LANGUAGE_FIELDS = [
    { name: 'language', label: t('onboarding.language') },
    { name: 'level', label: t('onboarding.level') },
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

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetchProfile()
      .then((data) => {
        if (cancelled) return
        setProfileFields({
          summary: data.summary || '',
          phone: data.phone || '',
          city: data.city || '',
          country_code: data.country_code || '',
          linkedin_url: data.linkedin_url || '',
        })
        setProfileCountry(data.country_code || '')
        const groupedExperiences = groupExperiencesByCompany(data.experiences)
        setCompanies(groupedExperiences)
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
        await updateProfile(formData, { isMultipart: true })
      } else {
        await updateProfile(profileFields)
      }

      await saveSection('experiences', flattenRoles(companies), initialExperienceIds)
      await saveSection('educations', flattenEducations(educations), initialEducationIds)

      for (const sectionKey of SECTION_KEYS) {
        await saveSection(sectionKey, sections[sectionKey], initialSectionIds[sectionKey])
      }

      setNotice(t('profile.saved'))
      setPhotoFile(null)
    } catch {
      setError(t('profile.saveError'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="mt-16 text-center text-sm text-muted-foreground">{t('common.loading')}</p>
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <Link to="/account" className="text-sm font-medium text-primary hover:underline">
        {t('profile.back')}
      </Link>

      <h1 className="text-3xl font-bold tracking-tight text-balance">{t('profile.title')}</h1>

      {error && (
        <p role="alert" className="rounded-md bg-destructive-soft px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="rounded-md bg-success-soft px-3 py-2 text-sm text-success">
          {notice}
        </p>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <Card>
          <CardContent className="flex flex-col gap-5 pt-6">
            <div className="flex flex-wrap gap-5">
              <div className="flex min-w-40 flex-1 flex-col gap-1.5">
                <Label htmlFor="first-name">{t('onboarding.firstName')}</Label>
                <Input
                  id="first-name"
                  type="text"
                  required
                  value={nameFields.first_name}
                  onChange={(event) => setNameFields({ ...nameFields, first_name: event.target.value })}
                />
              </div>
              <div className="flex min-w-40 flex-1 flex-col gap-1.5">
                <Label htmlFor="last-name">{t('onboarding.lastName')}</Label>
                <Input
                  id="last-name"
                  type="text"
                  required
                  value={nameFields.last_name}
                  onChange={(event) => setNameFields({ ...nameFields, last_name: event.target.value })}
                />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="summary">{t('profile.summary')}</Label>
              <Textarea
                id="summary"
                value={profileFields.summary}
                onChange={(event) => setProfileFields({ ...profileFields, summary: event.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="phone">{t('profile.phone')}</Label>
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
              <Label htmlFor="linkedin">{t('profile.linkedin')}</Label>
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
              <Label htmlFor="photo">{t('profile.photo')}</Label>
              <Input
                id="photo"
                type="file"
                accept="image/*"
                onChange={(event) => setPhotoFile(event.target.files[0] || null)}
              />
            </div>
          </CardContent>
        </Card>

        <ExperienceGroupEditor
          companies={companies}
          onChange={setCompanies}
          t={t}
          titleKey="profile.experiences"
          hintKey="profile.experiencesHint"
        />
        {companies.reduce((total, group) => total + group.roles.length, 0) > 5 && (
          <p role="status" className="text-sm text-muted-foreground">
            {t('profile.experiencesLimitWarning')}
          </p>
        )}

        <EducationListEditor rows={educations} onChange={setEducations} t={t} />

        {SECTION_KEYS.map((sectionKey) => (
          <ListSectionEditor
            key={sectionKey}
            title={SECTION_CONFIG[sectionKey].title}
            addLabel={SECTION_CONFIG[sectionKey].addLabel}
            removeLabel={t('profile.remove')}
            fields={SECTION_CONFIG[sectionKey].fields}
            rows={sections[sectionKey]}
            onChange={(rows) => setSections({ ...sections, [sectionKey]: rows })}
          />
        ))}

        <Button type="submit" disabled={saving} className="w-fit">
          {t('profile.save')}
        </Button>
      </form>
    </div>
  )
}
