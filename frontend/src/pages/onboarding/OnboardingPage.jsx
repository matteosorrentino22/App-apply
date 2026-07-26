import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { useLanguage } from '../../i18n/LanguageContext'
import { updateMe } from '../../api/auth'
import { updateProfile, importCv, createSectionItem } from '../../api/profile'
import { createSearch, activateSearch } from '../../api/searches'
import { ApiError } from '../../api/client'
import ListSectionEditor, { emptyRow } from '../../components/ListSectionEditor'

const SECTION_KEYS = ['experiences', 'educations', 'skills', 'certifications', 'languages']

function importedListToRows(items, fields) {
  return (items || []).map((item) => {
    const row = emptyRow(fields)
    for (const field of fields) {
      row[field.name] = item[field.name] ?? (field.type === 'lines' ? [] : '')
    }
    return row
  })
}

export default function OnboardingPage() {
  const { t } = useLanguage()
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [preferences, setPreferences] = useState({
    objective_statement: user?.objective_statement || '',
    cv_language_mode: user?.cv_language_mode || 'job_language',
    cv_include_photo: user?.cv_include_photo || false,
  })

  const [profileFields, setProfileFields] = useState({
    summary: '',
    key_achievements: '',
    phone: '',
    city: '',
    linkedin_url: '',
  })
  const [photoFile, setPhotoFile] = useState(null)
  const [cvNotice, setCvNotice] = useState('')

  const EXPERIENCE_FIELDS = [
    { name: 'company', label: t('onboarding.company') },
    { name: 'role', label: t('onboarding.role') },
    { name: 'location', label: t('onboarding.location') },
    { name: 'bullets', label: t('onboarding.bullets'), type: 'lines' },
  ]
  const EDUCATION_FIELDS = [
    { name: 'institution', label: t('onboarding.institution') },
    { name: 'title', label: t('onboarding.titleField') },
    { name: 'location', label: t('onboarding.location') },
    { name: 'dates', label: t('onboarding.dates') },
    { name: 'notes', label: t('onboarding.notes') },
  ]
  const SKILL_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const CERTIFICATION_FIELDS = [{ name: 'name', label: t('onboarding.name') }]
  const LANGUAGE_FIELDS = [
    { name: 'language', label: t('onboarding.language') },
    { name: 'level', label: t('onboarding.level') },
  ]

  const SECTION_CONFIG = {
    experiences: { fields: EXPERIENCE_FIELDS, title: t('onboarding.experiences'), addLabel: t('onboarding.addExperience') },
    educations: { fields: EDUCATION_FIELDS, title: t('onboarding.educations'), addLabel: t('onboarding.addEducation') },
    skills: { fields: SKILL_FIELDS, title: t('onboarding.skills'), addLabel: t('onboarding.addSkill') },
    certifications: { fields: CERTIFICATION_FIELDS, title: t('onboarding.certifications'), addLabel: t('onboarding.addCertification') },
    languages: { fields: LANGUAGE_FIELDS, title: t('onboarding.languages'), addLabel: t('onboarding.addLanguage') },
  }

  const [sections, setSections] = useState({
    experiences: [],
    educations: [],
    skills: [],
    certifications: [],
    languages: [],
  })

  const [search, setSearch] = useState({ name: '', keywords: '', location: '' })

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
        key_achievements: structured.key_achievements || '',
        phone: '',
        city: '',
        linkedin_url: '',
      })
      setSections({
        experiences: importedListToRows(structured.experiences, EXPERIENCE_FIELDS),
        educations: importedListToRows(structured.educations, EDUCATION_FIELDS),
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

      for (const sectionKey of SECTION_KEYS) {
        for (const row of sections[sectionKey]) {
          const { _key, ...payload } = row
          await createSectionItem(sectionKey, payload)
        }
      }

      setStep(3)
    } catch {
      setError(t('common.genericError'))
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
    <div className="onboarding-page">
      <h1>{t('onboarding.title')}</h1>
      <ol className="onboarding-steps">
        <li aria-current={step === 1 ? 'step' : undefined}>{t('onboarding.stepPreferences')}</li>
        <li aria-current={step === 2 ? 'step' : undefined}>{t('onboarding.stepProfile')}</li>
        <li aria-current={step === 3 ? 'step' : undefined}>{t('onboarding.stepSearch')}</li>
      </ol>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {step === 1 && (
        <form onSubmit={handlePreferencesSubmit}>
          <label>
            {t('onboarding.objectiveLabel')}
            <textarea
              placeholder={t('onboarding.objectivePlaceholder')}
              value={preferences.objective_statement}
              onChange={(event) =>
                setPreferences({ ...preferences, objective_statement: event.target.value })
              }
            />
          </label>
          <label>
            {t('onboarding.cvTemplateLabel')}
            <input type="text" value={t('onboarding.cvTemplateValue')} disabled readOnly />
          </label>
          <fieldset>
            <legend>{t('onboarding.cvLanguageLabel')}</legend>
            <label>
              <input
                type="radio"
                name="cv_language_mode"
                checked={preferences.cv_language_mode === 'job_language'}
                onChange={() => setPreferences({ ...preferences, cv_language_mode: 'job_language' })}
              />
              {t('onboarding.cvLanguageJob')}
            </label>
            <label>
              <input
                type="radio"
                name="cv_language_mode"
                checked={preferences.cv_language_mode === 'english'}
                onChange={() => setPreferences({ ...preferences, cv_language_mode: 'english' })}
              />
              {t('onboarding.cvLanguageEnglish')}
            </label>
          </fieldset>
          <label>
            <input
              type="checkbox"
              checked={preferences.cv_include_photo}
              onChange={(event) =>
                setPreferences({ ...preferences, cv_include_photo: event.target.checked })
              }
            />
            {t('onboarding.cvIncludePhotoLabel')}
          </label>
          <button type="submit" disabled={saving}>
            {t('onboarding.next')}
          </button>
        </form>
      )}

      {step === 2 && (
        <>
          <section className="cv-upload">
            <h2>{t('onboarding.uploadCvTitle')}</h2>
            <p>{t('onboarding.uploadCvHint')}</p>
            <input type="file" accept=".pdf,.docx" onChange={handleCvUpload} disabled={saving} />
            {cvNotice && <p role="status">{cvNotice}</p>}
          </section>

          <form onSubmit={handleProfileSubmit}>
            <label>
              {t('onboarding.profileSummary')}
              <textarea
                value={profileFields.summary}
                onChange={(event) => setProfileFields({ ...profileFields, summary: event.target.value })}
              />
            </label>
            <label>
              {t('onboarding.profileAchievements')}
              <textarea
                value={profileFields.key_achievements}
                onChange={(event) =>
                  setProfileFields({ ...profileFields, key_achievements: event.target.value })
                }
              />
            </label>
            <label>
              {t('onboarding.profilePhone')}
              <input
                type="text"
                value={profileFields.phone}
                onChange={(event) => setProfileFields({ ...profileFields, phone: event.target.value })}
              />
            </label>
            <label>
              {t('onboarding.profileCity')}
              <input
                type="text"
                value={profileFields.city}
                onChange={(event) => setProfileFields({ ...profileFields, city: event.target.value })}
              />
            </label>
            <label>
              {t('onboarding.profileLinkedin')}
              <input
                type="text"
                value={profileFields.linkedin_url}
                onChange={(event) =>
                  setProfileFields({ ...profileFields, linkedin_url: event.target.value })
                }
              />
            </label>
            <label>
              {t('onboarding.profilePhoto')}
              <input
                type="file"
                accept="image/*"
                onChange={(event) => setPhotoFile(event.target.files[0] || null)}
              />
            </label>

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

            <button type="submit" disabled={saving}>
              {t('onboarding.saveProfile')}
            </button>
          </form>
        </>
      )}

      {step === 3 && (
        <form onSubmit={handleSearchSubmit}>
          <h2>{t('onboarding.firstSearchTitle')}</h2>
          <p>{t('onboarding.firstSearchHint')}</p>
          <label>
            {t('onboarding.searchName')}
            <input
              type="text"
              value={search.name}
              onChange={(event) => setSearch({ ...search, name: event.target.value })}
              required
            />
          </label>
          <label>
            {t('onboarding.searchKeywords')}
            <input
              type="text"
              value={search.keywords}
              onChange={(event) => setSearch({ ...search, keywords: event.target.value })}
              required
            />
          </label>
          <label>
            {t('onboarding.searchLocation')}
            <input
              type="text"
              value={search.location}
              onChange={(event) => setSearch({ ...search, location: event.target.value })}
              required
            />
          </label>
          <button type="submit" disabled={saving}>
            {t('onboarding.finish')}
          </button>
        </form>
      )}
    </div>
  )
}
