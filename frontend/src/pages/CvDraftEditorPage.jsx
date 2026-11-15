import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchCvDraft,
  fetchJob,
  finalizeCvDraft,
  keepCvDraft,
  openCvDraft,
  previewCvDraft,
  updateCvDraft,
} from '../api/jobs'
import { fetchProfile } from '../api/profile'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import CvDraftChatPanel from '@/components/CvDraftChatPanel'
import EditorShell from '@/components/editor/EditorShell'
import EditorPreview from '@/components/editor/EditorPreview'
import OutdatedDraftModal from '@/components/editor/OutdatedDraftModal'
import {
  AreasSection,
  ChecklistSection,
  EducationsSection,
  ExperiencesSection,
  LanguagesSection,
  QualificationSection,
  SummarySection,
} from '@/components/editor/CvSections'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { cvChatApi } from '@/lib/draftChatApi'
import { useDraftChat } from '@/lib/useDraftChat'
import { getLanguageLevelOptions, getLanguageNameOptions } from '../utils/languageOptions'
import { newItemId } from '../utils/itemId'

// Editor della bozza del CV (Sprint 51–62, 69; ridisegnato nello Sprint 76:
// Docs/design/SCREENS.md §3, mockup `cv-editor`, `cv-preview`,
// `cv-assistant*`, `cv-outdated`, `desk-editor`). Stessa logica di prima:
// bozza aperta o riseminata, autosave + anteprima con un solo debounce,
// salvataggio prima della chat e della finalizzazione, azioni della chat
// applicate con le stesse funzioni dell'editor. Cambia la presentazione:
// sezioni a fisarmonica, Modifica / Anteprima, chat in colonna o pannello.

function moveItem(list, index, delta) {
  const target = index + delta
  if (target < 0 || target >= list.length) return list
  const next = [...list]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next
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
  const [mode, setMode] = useState('edit')
  // Sprint 69: c'è un CV più recente della bozza, l'utente sceglie se
  // riseminare o continuare prima di vedere l'editor.
  const [outdatedPrompt, setOutdatedPrompt] = useState(false)
  const [resolvingOutdated, setResolvingOutdated] = useState(false)
  // Bullet "puntati" come contesto per la chat (Sprint 61): clic sul
  // pulsante sotto la spunta mostra/nascondi di ciascun singolo bullet,
  // cumulabile su più bullet anche di esperienze diverse — niente di
  // persistito, si azzera lasciando la pagina. Chiave: l'id stabile del
  // bullet (Sprint 69), che resta giusto anche dopo riordini o eliminazioni.
  const [focusedBullets, setFocusedBullets] = useState([])

  function isBulletFocused(bulletId) {
    return focusedBullets.some((item) => item.bulletId === bulletId)
  }

  function toggleFocusBullet(profileExperienceId, bulletId) {
    setFocusedBullets((current) =>
      current.some((item) => item.bulletId === bulletId)
        ? current.filter((item) => item.bulletId !== bulletId)
        : [...current, { profileExperienceId, bulletId }],
    )
  }

  // Chat (Sprint 76): stato nella pagina, il pannello cambia solo contenitore.
  const chat = useDraftChat({
    jobId: id,
    api: cvChatApi,
    t,
    enabled: content != null,
    onApplyAction: (action) => applyChatAction(action),
    onBeforeSend: () => flushPendingSave(),
  })

  const debounceRef = useRef(null)
  const firstLoadRef = useRef(true)
  const previewUrlRef = useRef(null)
  // Contenuto con modifiche non ancora salvate dall'autosave (Sprint 69):
  // "Genera PDF finale" lo invia al server, la chat lo salva prima di
  // inviare il messaggio.
  const unsavedRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const jobData = await fetchJob(id)
        if (cancelled) return
        setJob(jobData)

        if (jobData.cv_draft_outdated) {
          setOutdatedPrompt(true)
        } else {
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
        }

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
    unsavedRef.current = content
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      unsavedRef.current = null
      updateCvDraft(id, content)
        .then(() => setSaveStatus('saved'))
        .catch(() => {
          unsavedRef.current = unsavedRef.current || content
          setSaveStatus('error')
        })
      runPreview(content)
    }, 1200)
    return () => clearTimeout(debounceRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content])

  // Salva subito l'eventuale modifica in attesa dell'autosave (Sprint 69).
  async function flushPendingSave() {
    if (!unsavedRef.current) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    const pending = unsavedRef.current
    unsavedRef.current = null
    try {
      await updateCvDraft(id, pending)
      setSaveStatus('saved')
    } catch {
      unsavedRef.current = pending
    }
  }

  async function resolveOutdated(restart) {
    setResolvingOutdated(true)
    try {
      const draftContent = restart ? await openCvDraft(id) : await keepCvDraft(id)
      firstLoadRef.current = true
      setContent(draftContent)
      setOutdatedPrompt(false)
    } catch {
      setError(t('cvEditor.openError'))
      setOutdatedPrompt(false)
    } finally {
      setResolvingOutdated(false)
    }
  }

  async function handleFinalize() {
    setFinalizing(true)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    try {
      // Il contenuto a schermo va nella richiesta: il server lo salva nella
      // bozza prima del rendering, nessuna modifica resta fuori (Sprint 69).
      const result = await finalizeCvDraft(id, content)
      unsavedRef.current = null
      showToast(
        result?.page_count > 1
          ? t('cvEditor.finalizeSuccessMultiPage').replace('{count}', result.page_count)
          : t('cvEditor.finalizeSuccess'),
      )
      navigate(`/jobs/${id}`)
    } catch {
      showToast(t('cvEditor.finalizeError'))
    } finally {
      setFinalizing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center pt-16">
        <Spinner size={28} />
      </div>
    )
  }

  if (outdatedPrompt) {
    return (
      <OutdatedDraftModal
        title={t('cvEditor.outdatedTitle')}
        hint={t('cvEditor.outdatedHint')}
        restartLabel={t('cvEditor.outdatedRestart')}
        busy={resolvingOutdated}
        onRestart={() => resolveOutdated(true)}
        onContinue={() => resolveOutdated(false)}
        onDismiss={() => navigate(`/jobs/${id}`)}
      />
    )
  }

  if (error || !content) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col items-start gap-4 px-4 py-8">
        <Banner variant="error" className="w-full">
          {error}
        </Banner>
        <Button variant="secondary" onClick={() => navigate(`/jobs/${id}`)}>
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
    updateExperience(expIndex, { bullets: [...exp.bullets, { id: newItemId(), text, shown: true }] })
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
  // Sprint 69: bullet ritrovati per id, aree per il testo che avevano al
  // momento della proposta (`area_text`); ritorna false se l'elemento non
  // c'è più (nessuna modifica applicata a un elemento diverso).
  function applyChatAction(action) {
    const expIndex = content.experiences.findIndex(
      (exp) => exp.profile_experience_id === action.profile_experience_id,
    )
    const bulletIndex =
      expIndex === -1 ? -1 : content.experiences[expIndex].bullets.findIndex((b) => b.id === action.bullet_id)
    const areaIndex =
      action.area_text != null ? content.areas_of_expertise.indexOf(action.area_text) : (action.area_index ?? -1)
    const inRange = (index, list) => Number.isInteger(index) && index >= 0 && index < list.length
    switch (action.type) {
      case 'update_summary':
        setField('summary', action.text)
        return true
      case 'update_qualification':
        setField('qualification', action.text)
        return true
      case 'update_role':
        if (expIndex === -1) return false
        updateExperience(expIndex, { role: action.text })
        return true
      case 'add_bullet':
        if (expIndex === -1) return false
        addBullet(expIndex, action.text)
        return true
      case 'update_bullet':
      case 'hide_bullet':
      case 'show_bullet':
        if (bulletIndex === -1) return false
        updateBullet(
          expIndex,
          bulletIndex,
          action.type === 'update_bullet' ? { text: action.text } : { shown: action.type === 'show_bullet' },
        )
        return true
      case 'hide_experience':
      case 'show_experience':
        if (expIndex === -1) return false
        updateExperience(expIndex, { shown: action.type === 'show_experience' })
        return true
      case 'update_area':
        if (!inRange(areaIndex, content.areas_of_expertise)) return false
        updateArea(areaIndex, action.text)
        return true
      case 'add_area':
        addArea(action.text)
        return true
      case 'remove_area':
        if (!inRange(areaIndex, content.areas_of_expertise)) return false
        removeArea(areaIndex)
        return true
      case 'toggle_skill':
        toggleSkill(action.name)
        return true
      case 'toggle_certification':
        toggleCertification(action.name)
        return true
      case 'update_education_notes':
        if (!inRange(action.education_index, content.educations)) return false
        updateEducation(action.education_index, { notes: action.text })
        return true
      case 'update_language_level':
        if (!inRange(action.language_index, content.languages)) return false
        updateLanguage(action.language_index, { level: action.level })
        return true
      default:
        return false
    }
  }

  const subtitle = [job?.title, job?.company].filter(Boolean).join(' · ')
  const sectionHandlers = { updateExperience, updateBullet, removeBullet, addBullet, moveBullet, toggleFocusBullet }

  const editor = (
    <div className="flex flex-col gap-3">
      <SummarySection value={content.summary} onChange={(text) => setField('summary', text)} />
      <QualificationSection value={content.qualification} onChange={(text) => setField('qualification', text)} />
      <AreasSection areas={content.areas_of_expertise} onUpdate={updateArea} onRemove={removeArea} onAdd={addArea} onMove={moveArea} />
      <ExperiencesSection experiences={content.experiences} isFocused={isBulletFocused} handlers={sectionHandlers} />
      <EducationsSection educations={content.educations} onUpdate={updateEducation} onRemove={removeEducation} onAdd={addEducation} />
      <ChecklistSection title={t('cvEditor.skillsLabel')} items={profileSkills} selected={content.skills} onToggle={toggleSkill} />
      <ChecklistSection
        title={t('cvEditor.certificationsLabel')}
        items={profileCertifications}
        selected={content.certifications}
        onToggle={toggleCertification}
      />
      <LanguagesSection
        languages={content.languages}
        nameOptions={languageNameOptions}
        levelOptions={languageLevelOptions}
        onUpdate={updateLanguage}
        onRemove={removeLanguage}
        onAdd={addLanguage}
      />
    </div>
  )

  return (
    <EditorShell
      jobId={id}
      saveStatus={saveStatus}
      title={t('cvEditor.navTitle')}
      subtitle={subtitle}
      pageCount={pageCount}
      multiPageText={pageCount > 1 ? t('cvEditor.multiPageHint').replace('{count}', pageCount) : null}
      mode={mode}
      onModeChange={setMode}
      editor={editor}
      preview={<EditorPreview previewUrl={previewUrl} unavailable={previewUnavailable} title={t('cvEditor.previewFrameTitle')} />}
      chatTitle={t('cvEditor.chatTitle')}
      renderChat={(showHeader) => (
        <CvDraftChatPanel
          chat={chat}
          content={content}
          focusedBullets={focusedBullets}
          onToggleFocus={toggleFocusBullet}
          showHeader={showHeader}
        />
      )}
      chatOpen={chatOpen}
      onChatOpenChange={setChatOpen}
      finalizeLabel={t('cvEditor.finalizeButton')}
      finalizing={finalizing}
      onFinalize={handleFinalize}
    />
  )
}
