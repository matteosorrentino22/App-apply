import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronDown, ChevronUp, Sparkles, Trash2 } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchCvDraft,
  fetchJob,
  finalizeCvDraft,
  openCvDraft,
  previewCvDraft,
  updateCvDraft,
} from '../api/jobs'
import { fetchProfile } from '../api/profile'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import RichBulletInput from '@/components/RichBulletInput'
import CvDraftChatPanel from '@/components/CvDraftChatPanel'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getLanguageLevelOptions, getLanguageNameOptions } from '../utils/languageOptions'

function moveItem(list, index, delta) {
  const target = index + delta
  if (target < 0 || target >= list.length) return list
  const next = [...list]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next
}

function ReorderButtons({ index, length, onMove, t }) {
  return (
    <div className="flex flex-col">
      <button
        type="button"
        disabled={index === 0}
        onClick={() => onMove(index, -1)}
        aria-label={t('cvEditor.moveUp')}
        className="text-muted-foreground hover:text-foreground disabled:opacity-30"
      >
        <ChevronUp className="h-4 w-4" />
      </button>
      <button
        type="button"
        disabled={index === length - 1}
        onClick={() => onMove(index, 1)}
        aria-label={t('cvEditor.moveDown')}
        className="text-muted-foreground hover:text-foreground disabled:opacity-30"
      >
        <ChevronDown className="h-4 w-4" />
      </button>
    </div>
  )
}

function SectionCard({ title, children }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </div>
  )
}

export default function CvDraftEditorPage() {
  const { id } = useParams()
  const { t, lang } = useLanguage()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [job, setJob] = useState(null)
  const [content, setContent] = useState(null)
  const [profileSkills, setProfileSkills] = useState([])
  const [profileCertifications, setProfileCertifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saveStatus, setSaveStatus] = useState('idle')
  const [previewUrl, setPreviewUrl] = useState(null)
  const [pageCount, setPageCount] = useState(null)
  const [previewUnavailable, setPreviewUnavailable] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  const debounceRef = useRef(null)
  const firstLoadRef = useRef(true)
  const previewUrlRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const jobData = await fetchJob(id)
        if (cancelled) return
        setJob(jobData)

        let draftContent
        try {
          draftContent = await fetchCvDraft(id)
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            draftContent = await openCvDraft(id)
          } else {
            throw err
          }
        }
        if (cancelled) return
        firstLoadRef.current = true
        setContent(draftContent)

        const profileData = await fetchProfile()
        if (cancelled) return
        setProfileSkills(profileData.skills || [])
        setProfileCertifications(profileData.certifications || [])
      } catch {
        if (!cancelled) setError(t('cvEditor.openError'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function runPreview(currentContent) {
    try {
      const { blob, pageCount: count } = await previewCvDraft(id, currentContent)
      setPreviewUnavailable(false)
      setPageCount(count)
      const nextUrl = URL.createObjectURL(blob)
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = nextUrl
      setPreviewUrl(nextUrl)
    } catch {
      setPreviewUnavailable(true)
    }
  }

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    }
  }, [])

  // Autosave + preview debounced insieme (Sprint 51): un solo giro di
  // attesa dopo che l'utente smette di modificare, non due timer separati
  // che corrono a velocità diverse.
  useEffect(() => {
    if (!content) return
    if (firstLoadRef.current) {
      firstLoadRef.current = false
      runPreview(content)
      return
    }
    setSaveStatus('saving')
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      updateCvDraft(id, content)
        .then(() => setSaveStatus('saved'))
        .catch(() => setSaveStatus('idle'))
      runPreview(content)
    }, 1200)
    return () => clearTimeout(debounceRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content])

  async function handleFinalize() {
    setFinalizing(true)
    try {
      await finalizeCvDraft(id)
      showToast(t('cvEditor.finalizeSuccess'))
      navigate(`/jobs/${id}`)
    } catch {
      showToast(t('cvEditor.finalizeError'))
    } finally {
      setFinalizing(false)
    }
  }

  if (loading) {
    return <p className="mt-16 text-center text-sm text-muted-foreground">{t('cvEditor.loading')}</p>
  }

  if (error || !content) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <p role="alert" className="rounded-md bg-destructive-soft px-3 py-2 text-sm text-destructive">
          {error}
        </p>
        <Button variant="secondary" className="mt-4" onClick={() => navigate(`/jobs/${id}`)}>
          {t('cvEditor.backToJob')}
        </Button>
      </div>
    )
  }

  function setField(field, value) {
    setContent((current) => ({ ...current, [field]: value }))
  }

  // --- Areas of expertise ---
  function updateArea(index, value) {
    const next = [...content.areas_of_expertise]
    next[index] = value
    setField('areas_of_expertise', next)
  }
  function removeArea(index) {
    setField('areas_of_expertise', content.areas_of_expertise.filter((_, i) => i !== index))
  }
  function addArea(text = '') {
    setField('areas_of_expertise', [...content.areas_of_expertise, text])
  }
  function moveArea(index, delta) {
    setField('areas_of_expertise', moveItem(content.areas_of_expertise, index, delta))
  }

  // --- Experiences / bullets ---
  function updateExperience(expIndex, patch) {
    const next = content.experiences.map((exp, i) => (i === expIndex ? { ...exp, ...patch } : exp))
    setField('experiences', next)
  }
  function updateBullet(expIndex, bulletIndex, patch) {
    const exp = content.experiences[expIndex]
    const bullets = exp.bullets.map((b, i) => (i === bulletIndex ? { ...b, ...patch } : b))
    updateExperience(expIndex, { bullets })
  }
  function removeBullet(expIndex, bulletIndex) {
    const exp = content.experiences[expIndex]
    updateExperience(expIndex, { bullets: exp.bullets.filter((_, i) => i !== bulletIndex) })
  }
  function addBullet(expIndex, text = '') {
    const exp = content.experiences[expIndex]
    updateExperience(expIndex, { bullets: [...exp.bullets, { text, shown: true }] })
  }
  function moveBullet(expIndex, bulletIndex, delta) {
    const exp = content.experiences[expIndex]
    updateExperience(expIndex, { bullets: moveItem(exp.bullets, bulletIndex, delta) })
  }

  // --- Education ---
  function updateEducation(index, patch) {
    const next = content.educations.map((edu, i) => (i === index ? { ...edu, ...patch } : edu))
    setField('educations', next)
  }
  function removeEducation(index) {
    setField('educations', content.educations.filter((_, i) => i !== index))
  }
  function addEducation() {
    setField('educations', [
      ...content.educations,
      { institution: '', title: '', location: '', dates: '', notes: '' },
    ])
  }

  // --- Skills / certifications ---
  function toggleSkill(name) {
    const has = content.skills.includes(name)
    setField('skills', has ? content.skills.filter((s) => s !== name) : [...content.skills, name])
  }
  function toggleCertification(name) {
    const has = content.certifications.includes(name)
    setField(
      'certifications',
      has ? content.certifications.filter((c) => c !== name) : [...content.certifications, name],
    )
  }

  // --- Languages ---
  const languageNameOptions = getLanguageNameOptions(lang)
  const languageLevelOptions = getLanguageLevelOptions(lang)
  function updateLanguage(index, patch) {
    const next = content.languages.map((item, i) => (i === index ? { ...item, ...patch } : item))
    setField('languages', next)
  }
  function removeLanguage(index) {
    setField('languages', content.languages.filter((_, i) => i !== index))
  }
  function addLanguage() {
    setField('languages', [
      ...content.languages,
      { language: languageNameOptions[0]?.value || 'en', level: 'elementary' },
    ])
  }

  // --- Chat AI (Sprint 59): applica una singola azione accettata dall'utente
  // richiamando le stesse funzioni di stato di sopra — mai una scrittura
  // diretta nel JSON, così autosave e preview restano quelle già esistenti.
  function applyChatAction(action) {
    const expIndex = content.experiences.findIndex(
      (exp) => exp.profile_experience_id === action.profile_experience_id,
    )
    switch (action.type) {
      case 'update_summary':
        setField('summary', action.text)
        break
      case 'update_qualification':
        setField('qualification', action.text)
        break
      case 'update_role':
        if (expIndex !== -1) updateExperience(expIndex, { role: action.text })
        break
      case 'update_bullet':
        if (expIndex !== -1) updateBullet(expIndex, action.bullet_index, { text: action.text })
        break
      case 'add_bullet':
        if (expIndex !== -1) addBullet(expIndex, action.text)
        break
      case 'hide_bullet':
        if (expIndex !== -1) updateBullet(expIndex, action.bullet_index, { shown: false })
        break
      case 'show_bullet':
        if (expIndex !== -1) updateBullet(expIndex, action.bullet_index, { shown: true })
        break
      case 'hide_experience':
        if (expIndex !== -1) updateExperience(expIndex, { shown: false })
        break
      case 'show_experience':
        if (expIndex !== -1) updateExperience(expIndex, { shown: true })
        break
      case 'update_area':
        updateArea(action.area_index, action.text)
        break
      case 'add_area':
        addArea(action.text)
        break
      case 'remove_area':
        removeArea(action.area_index)
        break
      case 'toggle_skill':
        toggleSkill(action.name)
        break
      case 'toggle_certification':
        toggleCertification(action.name)
        break
      case 'update_education_notes':
        updateEducation(action.education_index, { notes: action.text })
        break
      case 'update_language_level':
        updateLanguage(action.language_index, { level: action.level })
        break
      default:
        break
    }
  }

  const pageCountLabel =
    pageCount == null
      ? ''
      : pageCount <= 1
        ? t('cvEditor.pageCountOk')
        : t('cvEditor.pageCountWarning').replace('{count}', pageCount)

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <Link to={`/jobs/${id}`} className="text-sm font-medium text-primary hover:underline">
          {t('cvEditor.backToJob')}
        </Link>
        <span className="text-xs text-muted-foreground">
          {saveStatus === 'saving' ? t('cvEditor.saving') : saveStatus === 'saved' ? t('cvEditor.saved') : ''}
        </span>
      </div>

      <h1 className="text-2xl font-bold tracking-tight text-balance">
        {t('cvEditor.navTitle')} — {job?.title}
      </h1>

      {!chatOpen && (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-primary px-4 py-3 text-sm font-medium text-primary-foreground shadow-lg transition-transform hover:scale-105 hover:bg-primary/90"
        >
          <Sparkles className="h-4 w-4" />
          {t('cvEditor.chatToggle')}
        </button>
      )}

      {chatOpen && (
        <CvDraftChatPanel
          jobId={id}
          content={content}
          onApplyAction={applyChatAction}
          onClose={() => setChatOpen(false)}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-5">
          <SectionCard title={t('cvEditor.summaryLabel')}>
            <Textarea
              value={content.summary}
              onChange={(event) => setField('summary', event.target.value)}
              className="min-h-28"
            />
          </SectionCard>

          <SectionCard title={t('cvEditor.qualificationLabel')}>
            <Input value={content.qualification} onChange={(event) => setField('qualification', event.target.value)} />
          </SectionCard>

          <SectionCard title={t('cvEditor.areasLabel')}>
            <div className="flex flex-col gap-2">
              {content.areas_of_expertise.map((area, index) => (
                <div key={index} className="flex items-center gap-2">
                  <ReorderButtons index={index} length={content.areas_of_expertise.length} onMove={moveArea} t={t} />
                  <Input value={area} onChange={(event) => updateArea(index, event.target.value)} className="flex-1" />
                  <button type="button" onClick={() => removeArea(index)} className="text-muted-foreground hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <Button type="button" variant="secondary" size="sm" className="w-fit" onClick={addArea}>
                {t('cvEditor.addArea')}
              </Button>
            </div>
          </SectionCard>

          <SectionCard title={t('cvEditor.experiencesLabel')}>
            <div className="flex flex-col gap-5">
              {content.experiences.map((exp, expIndex) => (
                <div key={exp.profile_experience_id} className="rounded-lg border border-border p-4">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{exp.company}</p>
                      <p className="text-xs text-muted-foreground">
                        {exp.location}
                        {exp.location && exp.dates && ' | '}
                        {exp.dates}
                      </p>
                    </div>
                    <label className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={exp.shown}
                        onCheckedChange={(checked) => updateExperience(expIndex, { shown: checked === true })}
                      />
                      {t('cvEditor.showInCv')}
                    </label>
                  </div>

                  <div className="mb-3 flex flex-col gap-1.5">
                    <Label htmlFor={`role-${expIndex}`}>{t('cvEditor.roleLabel')}</Label>
                    <Input
                      id={`role-${expIndex}`}
                      value={exp.role}
                      onChange={(event) => updateExperience(expIndex, { role: event.target.value })}
                    />
                  </div>

                  <Label className="mb-1.5 block">{t('cvEditor.bulletsLabel')}</Label>
                  <div className="flex flex-col gap-2">
                    {exp.bullets.map((bullet, bulletIndex) => (
                      <div key={bulletIndex} className="flex items-start gap-2">
                        <ReorderButtons
                          index={bulletIndex}
                          length={exp.bullets.length}
                          onMove={(i, delta) => moveBullet(expIndex, i, delta)}
                          t={t}
                        />
                        <Checkbox
                          className="mt-2.5"
                          checked={bullet.shown}
                          onCheckedChange={(checked) =>
                            updateBullet(expIndex, bulletIndex, { shown: checked === true })
                          }
                        />
                        <RichBulletInput
                          value={bullet.text}
                          onChange={(text) => updateBullet(expIndex, bulletIndex, { text })}
                        />
                        <button
                          type="button"
                          onClick={() => removeBullet(expIndex, bulletIndex)}
                          className="mt-2.5 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="w-fit"
                      onClick={() => addBullet(expIndex)}
                    >
                      {t('cvEditor.addBullet')}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title={t('cvEditor.educationsLabel')}>
            <div className="flex flex-col gap-4">
              {content.educations.map((edu, index) => (
                <div key={index} className="flex flex-col gap-2 rounded-lg border border-border p-4">
                  <div className="flex flex-wrap gap-2">
                    <Input
                      value={edu.institution}
                      placeholder={t('cvEditor.institutionLabel')}
                      onChange={(event) => updateEducation(index, { institution: event.target.value })}
                      className="min-w-40 flex-1"
                    />
                    <Input
                      value={edu.title}
                      placeholder={t('cvEditor.educationTitleLabel')}
                      onChange={(event) => updateEducation(index, { title: event.target.value })}
                      className="min-w-40 flex-1"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Input
                      value={edu.location}
                      placeholder={t('cvEditor.educationLocationLabel')}
                      onChange={(event) => updateEducation(index, { location: event.target.value })}
                      className="min-w-32 flex-1"
                    />
                    <Input
                      value={edu.dates}
                      placeholder={t('cvEditor.educationDatesLabel')}
                      onChange={(event) => updateEducation(index, { dates: event.target.value })}
                      className="min-w-32 flex-1"
                    />
                  </div>
                  <Textarea
                    value={edu.notes}
                    placeholder={t('cvEditor.educationNotesLabel')}
                    onChange={(event) => updateEducation(index, { notes: event.target.value })}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="w-fit text-muted-foreground hover:text-destructive"
                    onClick={() => removeEducation(index)}
                  >
                    <Trash2 className="mr-1.5 h-4 w-4" />
                    {t('cvEditor.removeEducation')}
                  </Button>
                </div>
              ))}
              <Button type="button" variant="secondary" size="sm" className="w-fit" onClick={addEducation}>
                {t('cvEditor.addEducation')}
              </Button>
            </div>
          </SectionCard>

          <SectionCard title={t('cvEditor.skillsLabel')}>
            <div className="flex flex-col gap-1.5">
              {profileSkills.map((skill) => (
                <label key={skill.id} className="flex items-center gap-2.5 text-sm">
                  <Checkbox checked={content.skills.includes(skill.name)} onCheckedChange={() => toggleSkill(skill.name)} />
                  {skill.name}
                </label>
              ))}
            </div>
          </SectionCard>

          <SectionCard title={t('cvEditor.certificationsLabel')}>
            <div className="flex flex-col gap-1.5">
              {profileCertifications.map((cert) => (
                <label key={cert.id} className="flex items-center gap-2.5 text-sm">
                  <Checkbox
                    checked={content.certifications.includes(cert.name)}
                    onCheckedChange={() => toggleCertification(cert.name)}
                  />
                  {cert.name}
                </label>
              ))}
            </div>
          </SectionCard>

          <SectionCard title={t('cvEditor.languagesLabel')}>
            <div className="flex flex-col gap-2">
              {content.languages.map((item, index) => (
                <div key={index} className="flex flex-wrap items-end gap-2">
                  <div className="flex min-w-32 flex-1 flex-col gap-1.5">
                    <Label>{t('cvEditor.languageLabel')}</Label>
                    <Select value={item.language} onValueChange={(value) => updateLanguage(index, { language: value })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {languageNameOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex min-w-32 flex-1 flex-col gap-1.5">
                    <Label>{t('cvEditor.levelLabel')}</Label>
                    <Select value={item.level} onValueChange={(value) => updateLanguage(index, { level: value })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {languageLevelOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <button type="button" onClick={() => removeLanguage(index)} className="mb-1 text-muted-foreground hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <Button type="button" variant="secondary" size="sm" className="w-fit" onClick={addLanguage}>
                {t('cvEditor.addLanguage')}
              </Button>
            </div>
          </SectionCard>
        </div>

        <div className="flex flex-col gap-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t('cvEditor.previewLabel')}
              </h2>
              {pageCountLabel && (
                <span className={pageCount > 1 ? 'text-sm font-medium text-destructive' : 'text-sm font-medium text-success'}>
                  {pageCountLabel}
                </span>
              )}
            </div>
            {previewUnavailable ? (
              <p className="text-sm text-muted-foreground">{t('cvEditor.previewUnavailable')}</p>
            ) : previewUrl ? (
              <iframe title="CV preview" src={previewUrl} className="h-[70vh] w-full rounded-md border border-border" />
            ) : (
              <p className="text-sm text-muted-foreground">{t('cvEditor.loading')}</p>
            )}
          </div>

          <Button type="button" disabled={finalizing} onClick={handleFinalize} className="w-full">
            {finalizing ? t('cvEditor.finalizing') : t('cvEditor.finalizeButton')}
          </Button>
        </div>
      </div>
    </div>
  )
}
