import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchCoverLetterDraft,
  fetchJob,
  finalizeCoverLetterDraft,
  keepCoverLetterDraft,
  openCoverLetterDraft,
  previewCoverLetterDraft,
  updateCoverLetterDraft,
} from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import CoverLetterChatPanel from '@/components/CoverLetterChatPanel'
import EditorShell from '@/components/editor/EditorShell'
import EditorPreview from '@/components/editor/EditorPreview'
import OutdatedDraftModal from '@/components/editor/OutdatedDraftModal'
import { AddButton, MoveButtons, RemoveButton } from '@/components/editor/CvSections'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { coverLetterChatApi } from '@/lib/draftChatApi'
import { useDraftChat } from '@/lib/useDraftChat'
import { COVER_LETTER_LIMITS } from '../utils/draftLimits'
import { newItemId } from '../utils/itemId'

// Mirror semplificato di CvDraftEditorPage.jsx (Sprint 63): niente
// esperienze/bullet/skill/istruzione/lingue da gestire, solo un elenco di
// paragrafi — aggiungi/modifica/rimuovi/riordina, nessun "mostra/nascondi"
// (qui non esiste una selezione automatica da riflettere, a differenza
// del CV). Sprint 69: paragrafi `{id, text}` con id stabile, usato anche
// dalle azioni della chat; avviso "bozza superata" e salvataggio prima della
// finalizzazione come nell'editor del CV. Sprint 76: stesso impianto
// dell'editor del CV (EditorShell, mockup `cover-editor`), un riquadro per
// paragrafo con riordino, eliminazione e limiti del server.
function moveItem(list, index, delta) {
  const target = index + delta
  if (target < 0 || target >= list.length) return list
  const next = [...list]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next
}

export default function CoverLetterDraftEditorPage() {
  const { id } = useParams()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [job, setJob] = useState(null)
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saveStatus, setSaveStatus] = useState('idle')
  const [previewUrl, setPreviewUrl] = useState(null)
  const [pageCount, setPageCount] = useState(null)
  const [previewUnavailable, setPreviewUnavailable] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [mode, setMode] = useState('edit')
  const [outdatedPrompt, setOutdatedPrompt] = useState(false)
  const [resolvingOutdated, setResolvingOutdated] = useState(false)

  const chat = useDraftChat({
    jobId: id,
    api: coverLetterChatApi,
    t,
    enabled: content != null,
    onApplyAction: (action) => applyChatAction(action),
    onBeforeSend: () => flushPendingSave(),
  })

  const debounceRef = useRef(null)
  const firstLoadRef = useRef(true)
  const previewUrlRef = useRef(null)
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

        if (jobData.cover_letter_draft_outdated) {
          setOutdatedPrompt(true)
          return
        }
        let draftContent
        try {
          draftContent = await fetchCoverLetterDraft(id)
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            draftContent = await openCoverLetterDraft(id)
          } else {
            throw err
          }
        }
        if (cancelled) return
        firstLoadRef.current = true
        setContent(draftContent)
      } catch {
        if (!cancelled) setError(t('coverLetterEditor.openError'))
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
      const { blob, pageCount: count } = await previewCoverLetterDraft(id, currentContent)
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
      updateCoverLetterDraft(id, content)
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

  async function flushPendingSave() {
    if (!unsavedRef.current) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    const pending = unsavedRef.current
    unsavedRef.current = null
    try {
      await updateCoverLetterDraft(id, pending)
      setSaveStatus('saved')
    } catch {
      unsavedRef.current = pending
    }
  }

  async function resolveOutdated(restart) {
    setResolvingOutdated(true)
    try {
      const draftContent = restart ? await openCoverLetterDraft(id) : await keepCoverLetterDraft(id)
      firstLoadRef.current = true
      setContent(draftContent)
      setOutdatedPrompt(false)
    } catch {
      setError(t('coverLetterEditor.openError'))
      setOutdatedPrompt(false)
    } finally {
      setResolvingOutdated(false)
    }
  }

  async function handleFinalize() {
    setFinalizing(true)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    try {
      const result = await finalizeCoverLetterDraft(id, content)
      unsavedRef.current = null
      showToast(
        result?.page_count > 1
          ? t('cvEditor.finalizeSuccessMultiPage').replace('{count}', result.page_count)
          : t('coverLetterEditor.finalizeSuccess'),
      )
      navigate(`/jobs/${id}`)
    } catch {
      showToast(t('coverLetterEditor.finalizeError'))
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
        title={t('coverLetterEditor.outdatedTitle')}
        hint={t('coverLetterEditor.outdatedHint')}
        restartLabel={t('coverLetterEditor.outdatedRestart')}
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

  function updateParagraph(paragraphId, text) {
    setContent((current) => ({
      ...current,
      paragraphs: current.paragraphs.map((p) => (p.id === paragraphId ? { ...p, text } : p)),
    }))
  }
  function removeParagraph(paragraphId) {
    setContent((current) => ({ ...current, paragraphs: current.paragraphs.filter((p) => p.id !== paragraphId) }))
  }
  function addParagraph(text = '') {
    setContent((current) => ({ ...current, paragraphs: [...current.paragraphs, { id: newItemId(), text }] }))
  }
  function moveParagraph(index, delta) {
    setContent((current) => ({ ...current, paragraphs: moveItem(current.paragraphs, index, delta) }))
  }

  // Le azioni della chat puntano al paragrafo per id (Sprint 69): accettare
  // più modifiche/rimozioni dello stesso turno colpisce sempre quello giusto.
  function applyChatAction(action) {
    const exists = content.paragraphs.some((p) => p.id === action.paragraph_id)
    switch (action.type) {
      case 'update_paragraph':
        if (!exists) return false
        updateParagraph(action.paragraph_id, action.text)
        return true
      case 'add_paragraph':
        addParagraph(action.text)
        return true
      case 'remove_paragraph':
        if (!exists) return false
        removeParagraph(action.paragraph_id)
        return true
      default:
        return false
    }
  }

  const count = content.paragraphs.length
  function paragraphTitle(index) {
    const base = t('coverLetterEditor.paragraphN').replace('{n}', index + 1)
    if (count < 2) return base
    if (index === 0) return `${base} · ${t('coverLetterEditor.paragraphOpening')}`
    if (index === count - 1) return `${base} · ${t('coverLetterEditor.paragraphClosing')}`
    return base
  }

  const editor = (
    <section aria-labelledby="paragraphs-title" className="flex flex-col gap-3">
      <h2 id="paragraphs-title" className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
        {t('coverLetterEditor.paragraphsLabel')}
      </h2>
      {content.paragraphs.map((paragraph, index) => {
        const fieldId = `paragraph-${paragraph.id || index}`
        return (
          <div key={paragraph.id || index} data-testid="cover-letter-paragraph" className="flex flex-col gap-3 rounded-card border border-border bg-card p-4 shadow-card">
            <div className="flex items-center justify-between gap-2">
              <label htmlFor={fieldId} className="min-w-0 text-sm font-bold text-label">
                {paragraphTitle(index)}
              </label>
              <div className="-mr-2 flex items-center">
                <MoveButtons index={index} length={count} onMove={moveParagraph} />
                <RemoveButton label={t('coverLetterEditor.removeParagraph')} onClick={() => removeParagraph(paragraph.id)} />
              </div>
            </div>
            <Textarea
              id={fieldId}
              value={paragraph.text}
              maxLength={COVER_LETTER_LIMITS.paragraphText}
              onChange={(event) => updateParagraph(paragraph.id, event.target.value)}
              className="min-h-32"
            />
          </div>
        )
      })}
      <AddButton
        label={t('coverLetterEditor.addParagraph')}
        onClick={() => addParagraph()}
        atLimit={count >= COVER_LETTER_LIMITS.paragraphs}
        limitText={t('coverLetterEditor.limitParagraphs').replace('{max}', COVER_LETTER_LIMITS.paragraphs)}
      />
    </section>
  )

  return (
    <EditorShell
      jobId={id}
      saveStatus={saveStatus}
      title={t('coverLetterEditor.navTitle')}
      subtitle={[job?.title, job?.company].filter(Boolean).join(' · ')}
      pageCount={pageCount}
      multiPageText={pageCount > 1 ? t('coverLetterEditor.multiPageHint').replace('{count}', pageCount) : null}
      mode={mode}
      onModeChange={setMode}
      editor={editor}
      preview={
        <EditorPreview previewUrl={previewUrl} unavailable={previewUnavailable} title={t('coverLetterEditor.previewFrameTitle')} />
      }
      chatTitle={t('coverLetterEditor.chatTitle')}
      renderChat={(showHeader) => <CoverLetterChatPanel chat={chat} content={content} showHeader={showHeader} />}
      chatOpen={chatOpen}
      onChatOpenChange={setChatOpen}
      finalizeLabel={t('coverLetterEditor.finalizeButton')}
      finalizing={finalizing}
      onFinalize={handleFinalize}
    />
  )
}
