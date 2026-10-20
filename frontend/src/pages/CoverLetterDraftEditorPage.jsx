import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronDown, ChevronUp, Sparkles, Trash2 } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchCoverLetterDraft,
  fetchJob,
  finalizeCoverLetterDraft,
  openCoverLetterDraft,
  previewCoverLetterDraft,
  updateCoverLetterDraft,
} from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import CoverLetterChatPanel from '@/components/CoverLetterChatPanel'

// Mirror semplificato di CvDraftEditorPage.jsx (Sprint 63): niente
// esperienze/bullet/skill/istruzione/lingue da gestire, solo un elenco di
// paragrafi — aggiungi/modifica/rimuovi/riordina, nessun "mostra/nascondi"
// (qui non esiste una selezione automatica da riflettere, a differenza
// del CV).
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
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      updateCoverLetterDraft(id, content)
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
      await finalizeCoverLetterDraft(id)
      showToast(t('coverLetterEditor.finalizeSuccess'))
      navigate(`/jobs/${id}`)
    } catch {
      showToast(t('coverLetterEditor.finalizeError'))
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

  function updateParagraph(index, text) {
    const next = content.paragraphs.map((p, i) => (i === index ? text : p))
    setContent((current) => ({ ...current, paragraphs: next }))
  }
  function removeParagraph(index) {
    setContent((current) => ({ ...current, paragraphs: current.paragraphs.filter((_, i) => i !== index) }))
  }
  function addParagraph(text = '') {
    setContent((current) => ({ ...current, paragraphs: [...current.paragraphs, text] }))
  }
  function moveParagraph(index, delta) {
    setContent((current) => ({ ...current, paragraphs: moveItem(current.paragraphs, index, delta) }))
  }

  function applyChatAction(action) {
    switch (action.type) {
      case 'update_paragraph':
        updateParagraph(action.paragraph_index, action.text)
        break
      case 'add_paragraph':
        addParagraph(action.text)
        break
      case 'remove_paragraph':
        removeParagraph(action.paragraph_index)
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
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <Link to={`/jobs/${id}`} className="text-sm font-medium text-primary hover:underline">
          {t('cvEditor.backToJob')}
        </Link>
        <span className="text-xs text-muted-foreground">
          {saveStatus === 'saving' ? t('cvEditor.saving') : saveStatus === 'saved' ? t('cvEditor.saved') : ''}
        </span>
      </div>

      <h1 className="text-2xl font-bold tracking-tight text-balance">
        {t('coverLetterEditor.navTitle')} — {job?.title}
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

      <CoverLetterChatPanel
        open={chatOpen}
        jobId={id}
        content={content}
        onApplyAction={applyChatAction}
        onClose={() => setChatOpen(false)}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <Label className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t('coverLetterEditor.paragraphsLabel')}
          </Label>
          {content.paragraphs.map((paragraph, index) => (
            <div key={index} className="flex items-start gap-2 rounded-lg border border-border p-3">
              <div className="flex flex-col">
                <button
                  type="button"
                  disabled={index === 0}
                  onClick={() => moveParagraph(index, -1)}
                  aria-label={t('cvEditor.moveUp')}
                  className="text-muted-foreground hover:text-foreground disabled:opacity-30"
                >
                  <ChevronUp className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  disabled={index === content.paragraphs.length - 1}
                  onClick={() => moveParagraph(index, 1)}
                  aria-label={t('cvEditor.moveDown')}
                  className="text-muted-foreground hover:text-foreground disabled:opacity-30"
                >
                  <ChevronDown className="h-4 w-4" />
                </button>
              </div>
              <Textarea
                value={paragraph}
                onChange={(event) => updateParagraph(index, event.target.value)}
                className="min-h-24 flex-1"
              />
              <button
                type="button"
                onClick={() => removeParagraph(index)}
                className="mt-2.5 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
          <Button type="button" variant="secondary" size="sm" className="w-fit" onClick={() => addParagraph()}>
            {t('coverLetterEditor.addParagraph')}
          </Button>
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
              <iframe title="Cover letter preview" src={previewUrl} className="h-[70vh] w-full rounded-md border border-border" />
            ) : (
              <p className="text-sm text-muted-foreground">{t('cvEditor.loading')}</p>
            )}
          </div>

          <Button type="button" disabled={finalizing} onClick={handleFinalize} className="w-full">
            {finalizing ? t('cvEditor.finalizing') : t('coverLetterEditor.finalizeButton')}
          </Button>
        </div>
      </div>
    </div>
  )
}
