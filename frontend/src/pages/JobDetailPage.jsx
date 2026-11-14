import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Archive,
  ArchiveRestore,
  ArrowUpRight,
  Check,
  ChevronLeft,
  FileText,
  Heart,
  MessageSquare,
  MoreHorizontal,
  Send,
  Sparkles,
  X,
} from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import {
  archiveJob,
  favoriteJob,
  fetchCoverLetterInstructions,
  fetchJob,
  fetchReferralMessageInstructions,
  fetchReferralMessages,
  generateCoverLetter,
  generateCv,
  generateReferralMessage,
  markApplicationDone,
  unarchiveJob,
  undoApplicationDone,
  unfavoriteJob,
} from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { useCostConfirm } from '@/components/CostConfirmDialog'
import RecruiterIcon from '@/components/RecruiterIcon'
import CoverLetterSheet from '@/components/job-detail/CoverLetterSheet'
import DocumentsSection from '@/components/job-detail/DocumentsSection'
import GapSheet from '@/components/job-detail/GapSheet'
import ReferralSheet from '@/components/job-detail/ReferralSheet'
import { DescriptionSection, ScoreSection } from '@/components/job-detail/ScoreSection'
import { ActionBar } from '@/components/ui/action-bar'
import { Badge } from '@/components/ui/badge'
import { Banner } from '@/components/ui/banner'
import { Button, buttonVariants } from '@/components/ui/button'
import { Menu } from '@/components/ui/menu'
import { Modal, ModalActions, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'
import { ScoreChip } from '@/components/ui/score-chip'
import { Spinner } from '@/components/ui/spinner'
import { SplitButton } from '@/components/ui/split-button'
import { useUsage } from '@/lib/usage'
import { cn } from '@/lib/utils'
import { applicantsLabel, isLowApplicants } from '../utils/applicants'
import { formatShortDate } from '../utils/date'
import { joinInstructions } from '../utils/generationLimits'
import { jobListHref } from '../utils/jobListUrl'

// Dettaglio job (Sprint 75, redesign: Docs/design/SCREENS.md §2, mockup
// `detail-*`, `generazione-in-corso`, `undo-application`, `confirm-cost`,
// `desk-detail`). Stesso comportamento di prima, nuova presentazione:
// testata con stato solo indicativo, punteggio e motivazione troncata,
// contatori espandibili, descrizione a fisarmonica, sezione Documenti,
// barra azione in basso al posto della barra di tab (Genera CV ▾ →
// Segna candidatura fatta → Annulla candidatura), menu ⋯ (archivio).
// Le generazioni restano sincrone: durante l'attesa una finestra non
// chiudibile con indicatore, nessun cambio a flussi né guardia di
// concorrenza (§5.2 tecniche).

const SIGNED_URL_REFRESH_MS = 20 * 60 * 1000

const EMPTY_REFERRAL_FORM = { channel: 'linkedin', recipientName: '', recipientLinkedinUrl: '', instructions: '' }

const GENERATION_TEXT = {
  cv: ['jobs.generateCv', 'jobs.generatingCvTitle', 'jobs.generatingCvText'],
  cover_letter: ['jobs.coverLetterDialogTitle', 'jobs.generatingCoverLetterTitle', 'jobs.generatingCoverLetterText'],
  referral_message: ['jobs.referralDialogTitle', 'jobs.generatingMessageTitle', 'jobs.generatingMessageText'],
}

// Attesa della generazione sincrona (mockup `generazione-in-corso`): non si
// chiude con Esc né toccando fuori, sparisce a risposta arrivata.
function GenerationModal({ kind }) {
  const { t } = useLanguage()
  const [titleKey, headingKey, textKey] = GENERATION_TEXT[kind || 'cv']
  const prevent = (event) => event.preventDefault()
  return (
    <Modal open={kind !== null}>
      <ModalContent onEscapeKeyDown={prevent} onPointerDownOutside={prevent} onInteractOutside={prevent} className="gap-5 pb-8">
        <ModalTitle>{t(titleKey)}</ModalTitle>
        <div className="flex flex-col items-center gap-3 text-center">
          <Spinner framed />
          <p className="text-lg font-bold text-foreground">{t(headingKey)}</p>
          <ModalDescription className="text-[15px]">{t(textKey)}</ModalDescription>
        </div>
      </ModalContent>
    </Modal>
  )
}

function StatusChip({ job, cvBusy }) {
  const { t } = useLanguage()
  // Chip solo indicativo (non selezionabile, nessuna freccia): lo stato
  // cambia con le azioni della pagina. "CV in generazione" è lo stato
  // transitorio (§4.10), mostrato mentre il CV si sta generando (da questa
  // pagina o secondo il server).
  if (cvBusy) {
    return (
      <span data-testid="job-status-badge" className="inline-flex min-h-8 w-fit items-center gap-1.5 rounded-full bg-primary-soft px-3 text-sm font-semibold text-primary">
        <Spinner size={14} label={t('jobs.statusCvGenerating')} />
        {t('jobs.statusCvGenerating')}
      </span>
    )
  }
  const done = job.status !== 'new'
  return (
    <span
      data-testid="job-status-badge"
      className={cn(
        'inline-flex min-h-8 w-fit items-center gap-1.5 rounded-full px-3 text-sm font-semibold',
        done ? 'bg-primary-soft text-primary' : 'bg-chip text-chip-foreground',
      )}
    >
      {done ? <Check className="h-4 w-4" strokeWidth={2.4} aria-hidden="true" /> : null}
      {t(`jobs.status_${job.status}`)}
    </span>
  )
}

export default function JobDetailPage() {
  const { id } = useParams()
  const { t, lang } = useLanguage()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { confirmCost, costDialog } = useCostConfirm()
  // Costo della prossima richiesta (Sprint 70): pannelli e conferma.
  const { usage, refresh: refreshUsage } = useUsage()

  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  // Generazione in attesa di risposta: 'cv' | 'cover_letter' | 'referral_message'.
  const [generating, setGenerating] = useState(null)
  const [marking, setMarking] = useState(false)
  const [undoOpen, setUndoOpen] = useState(false)

  const [gapSheetOpen, setGapSheetOpen] = useState(false)
  const [selectedGaps, setSelectedGaps] = useState([])
  const [gapInstructions, setGapInstructions] = useState('')

  const [coverLetterOpen, setCoverLetterOpen] = useState(false)
  const [coverLetterText, setCoverLetterText] = useState('')
  const [pastInstructions, setPastInstructions] = useState([])
  const [selectedPastInstructions, setSelectedPastInstructions] = useState([])

  const [referralOpen, setReferralOpen] = useState(false)
  const [referralForm, setReferralForm] = useState(EMPTY_REFERRAL_FORM)
  const [referralPastInstructions, setReferralPastInstructions] = useState([])
  const [selectedReferralPastInstructions, setSelectedReferralPastInstructions] = useState([])
  const [referralMessages, setReferralMessages] = useState([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetchJob(id)
      .then((jobData) => {
        if (!cancelled) setJob(jobData)
      })
      .catch(() => {
        if (!cancelled) setError(t('jobs.notFound'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    fetchReferralMessages(id)
      .then((messages) => {
        if (!cancelled) setReferralMessages(messages)
      })
      .catch(() => {
        if (!cancelled) setReferralMessages([])
      })
    return () => {
      cancelled = true
    }
  }, [id, t])

  // Gli URL di download di CV e cover letter sono firmati e scadono dopo
  // un'ora (Sprint 66): con la pagina aperta a lungo, o ripresa dopo ore
  // dallo sfondo, il job si ricarica così i pulsanti non portano a un 404.
  useEffect(() => {
    const refresh = () => fetchJob(id).then(setJob).catch(() => {})
    const timer = setInterval(refresh, SIGNED_URL_REFRESH_MS)
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [id])

  // Archivia / preferito rispondono con il serializer della lista, senza i
  // campi del dettaglio (pagine, modificabilità): si aggiorna solo il campo
  // cambiato. Prima dello Sprint 75 il preferito sostituiva l'intero job e
  // "Modifica CV" e gli avvisi sparivano fino al ricaricamento.
  function mergeJob(fields) {
    setJob((current) => ({ ...current, ...fields }))
  }

  function toggleGap(number) {
    setSelectedGaps((current) =>
      current.includes(number) ? current.filter((item) => item !== number) : [...current, number],
    )
  }

  function toggleIn(setter) {
    return (text) => setter((current) => (current.includes(text) ? current.filter((item) => item !== text) : [...current, text]))
  }

  function multiPageToast(key, pageCount) {
    if (pageCount > 1) showToast(t(key).replace('{count}', pageCount))
  }

  // Il backend distingue più cause dietro lo stesso 409 (concorrenza,
  // profilo incompleto, massimale/credito esaurito): il messaggio esatto
  // arriva in `detail`, non va sostituito con un testo fisso.
  function generationError(err, fallbackKey) {
    if (err instanceof ApiError && err.status === 409) showToast(err.data?.detail || t('jobs.generationConflict'))
    else showToast(t(fallbackKey))
  }

  async function handleGenerateCv() {
    if (!(await confirmCost(usage, 'cv'))) return
    setGapSheetOpen(false)
    setGenerating('cv')
    try {
      const result = await generateCv(id, selectedGaps, gapInstructions)
      setJob(await fetchJob(id))
      multiPageToast('jobs.cvMultiPageWarning', result?.page_count)
      setSelectedGaps([])
      setGapInstructions('')
    } catch (err) {
      generationError(err, 'jobs.generationFailed')
    } finally {
      refreshUsage()
      setGenerating(null)
    }
  }

  function openCoverLetter() {
    setCoverLetterText('')
    setSelectedPastInstructions([])
    setCoverLetterOpen(true)
    fetchCoverLetterInstructions()
      .then((data) => setPastInstructions(data.instructions || []))
      .catch(() => setPastInstructions([]))
  }

  async function handleGenerateCoverLetter() {
    if (!(await confirmCost(usage, 'cover_letter'))) return
    setCoverLetterOpen(false)
    setGenerating('cover_letter')
    try {
      const result = await generateCoverLetter(id, joinInstructions(selectedPastInstructions, coverLetterText))
      setJob(await fetchJob(id))
      multiPageToast('jobs.coverLetterMultiPageWarning', result?.page_count)
    } catch (err) {
      generationError(err, 'jobs.coverLetterGenerationFailed')
    } finally {
      refreshUsage()
      setGenerating(null)
    }
  }

  function openReferral() {
    setReferralForm(EMPTY_REFERRAL_FORM)
    setSelectedReferralPastInstructions([])
    setReferralOpen(true)
    fetchReferralMessageInstructions()
      .then((data) => setReferralPastInstructions(data.instructions || []))
      .catch(() => setReferralPastInstructions([]))
  }

  async function handleGenerateReferral() {
    if (!(await confirmCost(usage, 'referral_message'))) return
    setReferralOpen(false)
    setGenerating('referral_message')
    try {
      const message = await generateReferralMessage(id, {
        channel: referralForm.channel,
        recipient_name: referralForm.recipientName.trim(),
        recipient_linkedin_url: referralForm.recipientLinkedinUrl.trim(),
        instructions: joinInstructions(selectedReferralPastInstructions, referralForm.instructions),
      })
      setReferralMessages((current) => [message, ...current])
    } catch (err) {
      generationError(err, 'jobs.referralGenerationFailed')
    } finally {
      refreshUsage()
      setGenerating(null)
    }
  }

  async function handleCopyMessage(message) {
    const text = message.subject
      ? `${t('jobs.referralSubjectPrefix')} ${message.subject}\n\n${message.content}`
      : message.content
    try {
      await navigator.clipboard.writeText(text)
      showToast(t('jobs.referralCopied'))
    } catch {
      showToast(t('jobs.referralCopyFailed'))
    }
  }

  async function handleToggleFavorite() {
    const nextFavorite = !job.is_favorite
    mergeJob({ is_favorite: nextFavorite })
    try {
      const updated = nextFavorite ? await favoriteJob(id) : await unfavoriteJob(id)
      mergeJob({ is_favorite: updated.is_favorite })
    } catch {
      mergeJob({ is_favorite: !nextFavorite })
      showToast(t('common.genericError'))
    }
  }

  // Archivio dal menu ⋯ (SPEC-DELTA A7): stesso effetto dello swipe della
  // lista, raggiungibile anche da tastiera; si resta sul dettaglio.
  async function handleArchive() {
    try {
      const updated = await archiveJob(id)
      mergeJob({ is_archived: updated.is_archived })
      showToast(t('jobs.archivedToast'), {
        action: {
          label: t('jobs.undo'),
          onClick: async () => {
            const restored = await unarchiveJob(id)
            mergeJob({ is_archived: restored.is_archived })
          },
        },
      })
    } catch {
      showToast(t('common.genericError'))
    }
  }

  async function handleUnarchive() {
    try {
      const updated = await unarchiveJob(id)
      mergeJob({ is_archived: updated.is_archived })
      showToast(t('jobs.unarchivedToast'))
    } catch {
      showToast(t('common.genericError'))
    }
  }

  async function handleMarkApplicationDone() {
    setMarking(true)
    try {
      setJob(await markApplicationDone(id))
    } catch (err) {
      showToast(err instanceof ApiError && err.status === 409 ? t('jobs.applicationRejected') : t('common.genericError'))
    } finally {
      setMarking(false)
    }
  }

  async function handleUndoApplicationDone() {
    setMarking(true)
    try {
      setJob(await undoApplicationDone(id))
      setUndoOpen(false)
    } catch {
      showToast(t('jobs.undoApplicationFailed'))
    } finally {
      setMarking(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center pt-16">
        <Spinner size={28} />
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col items-start gap-4 px-4 py-8">
        <Banner variant="error" className="w-full">
          {error || t('jobs.notFound')}
        </Banner>
        <Button variant="secondary" onClick={() => navigate(jobListHref())}>
          {t('jobs.backToList')}
        </Button>
      </div>
    )
  }

  const hasCv = Boolean(job.cv_pdf_url)
  const applied = job.status === 'application_done'
  const cvBusy = generating === 'cv' || Boolean(job.cv_generation_in_progress)
  const coverLetterBusy = generating === 'cover_letter' || Boolean(job.cover_letter_generation_in_progress)
  const referralBusy = generating === 'referral_message' || Boolean(job.referral_message_generation_in_progress)
  const applicantsText = applicantsLabel(job, t)
  const showDocuments =
    hasCv || Boolean(job.cover_letter_pdf_url) || referralMessages.length > 0 || cvBusy || coverLetterBusy || applied

  const headerMenuItems = [
    job.is_archived
      ? { key: 'unarchive', label: t('jobs.restoreFromArchive'), icon: ArchiveRestore, onSelect: handleUnarchive }
      : { key: 'archive', label: t('jobs.archive'), icon: Archive, onSelect: handleArchive },
    // Senza CV la barra mostra "Genera CV": "Segna candidatura fatta"
    // (consentito anche senza CV, §4.10) resta raggiungibile da qui.
    !hasCv && !applied
      ? { key: 'mark', label: t('jobs.markApplicationDone'), icon: Send, onSelect: handleMarkApplicationDone, disabled: marking }
      : null,
  ].filter(Boolean)

  const generateMenuItems = [
    { key: 'cover-letter', label: t('jobs.generateCoverLetter'), icon: FileText, onSelect: openCoverLetter, disabled: coverLetterBusy },
    { key: 'message', label: t('jobs.generateReferralMessage'), icon: MessageSquare, onSelect: openReferral, disabled: referralBusy },
  ]

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 pb-6 pt-3 lg:pt-6">
      <div className="flex items-center justify-between gap-2">
        <Link
          to={jobListHref()}
          className="-ml-2 flex min-h-11 items-center gap-1 rounded-field px-2 text-base font-semibold text-primary outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/30"
        >
          <ChevronLeft className="h-5 w-5" aria-hidden="true" />
          {t('jobs.navLink')}
        </Link>
        <div className="flex items-center">
          <button
            type="button"
            onClick={handleToggleFavorite}
            aria-label={job.is_favorite ? t('jobs.unfavorite') : t('jobs.favorite')}
            aria-pressed={job.is_favorite}
            className="inline-flex h-11 w-11 items-center justify-center rounded-field text-foreground outline-none hover:bg-tint focus-visible:ring-3 focus-visible:ring-ring/30"
          >
            <Heart className={cn('h-6 w-6', job.is_favorite && 'fill-rose-500 text-rose-500')} aria-hidden="true" />
          </button>
          <Menu
            label={t('jobs.moreActions')}
            items={headerMenuItems}
            trigger={(props) => (
              <button
                {...props}
                aria-label={t('jobs.moreActions')}
                className="-mr-2 inline-flex h-11 w-11 items-center justify-center rounded-field text-foreground outline-none hover:bg-tint focus-visible:ring-3 focus-visible:ring-ring/30"
              >
                <MoreHorizontal className="h-6 w-6" aria-hidden="true" />
              </button>
            )}
          />
        </div>
      </div>

      <header className="flex flex-col gap-3">
        <StatusChip job={job} cvBusy={cvBusy} />
        <div className="flex items-start justify-between gap-4">
          <h1 className="min-w-0 break-words text-[26px] font-bold leading-[1.15] tracking-[-0.01em] text-foreground lg:text-[28px]">
            {job.title}
          </h1>
          {job.score != null ? <ScoreChip score={job.score} size="lg" /> : null}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <p className="min-w-0 text-base text-muted-foreground">
            {job.company}
            {job.location ? <> · {job.location}</> : null}
            {job.salary ? <> · {job.salary}</> : null}
            <RecruiterIcon job={job} />
          </p>
          {job.apply_url ? (
            <a
              href={job.apply_url}
              target="_blank"
              rel="noreferrer"
              aria-label={t('jobs.openApplyLink')}
              className={cn(buttonVariants({ variant: 'secondary' }), 'ml-auto rounded-full')}
            >
              {t('jobs.listingButton')}
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </a>
          ) : null}
        </div>
        {applicantsText || job.matched_search || job.is_archived || job.date_collected ? (
          <div className="flex flex-wrap items-center gap-2">
            {applicantsText ? <Badge variant={isLowApplicants(job) ? 'success' : 'neutral'}>{applicantsText}</Badge> : null}
            {job.matched_search ? (
              <Badge variant="neutral" className="whitespace-normal break-words">
                {t('jobs.foundWith').replace('{search}', job.matched_search)}
              </Badge>
            ) : null}
            {job.is_archived ? <Badge variant="neutral">{t('jobs.archivedBadge')}</Badge> : null}
            {job.date_collected ? (
              <span className="text-xs text-muted-foreground">
                {t('jobs.importedOnPrefix')} {formatShortDate(job.date_collected, lang)}
              </span>
            ) : null}
          </div>
        ) : null}
      </header>

      {showDocuments ? (
        <DocumentsSection
          job={job}
          messages={referralMessages}
          cvBusy={cvBusy}
          coverLetterBusy={coverLetterBusy}
          referralBusy={referralBusy}
          onGenerateCv={() => setGapSheetOpen(true)}
          onGenerateCoverLetter={openCoverLetter}
          onGenerateReferral={openReferral}
          onCopyMessage={handleCopyMessage}
        />
      ) : null}

      <ScoreSection job={job} />
      <DescriptionSection description={job.description} />

      <ActionBar>
        {applied ? (
          <Button variant="secondary" size="lg" className="border-primary" disabled={marking} onClick={() => setUndoOpen(true)}>
            <X className="h-5 w-5" aria-hidden="true" />
            {t('jobs.undoApplication')}
          </Button>
        ) : hasCv ? (
          <Button size="lg" disabled={marking} onClick={handleMarkApplicationDone}>
            <Check className="h-5 w-5" aria-hidden="true" />
            {t('jobs.markApplicationDone')}
          </Button>
        ) : (
          <SplitButton
            icon={Sparkles}
            onClick={() => setGapSheetOpen(true)}
            disabled={cvBusy}
            menuLabel={t('jobs.generateMenuLabel')}
            items={generateMenuItems}
          >
            {cvBusy ? t('jobs.generating') : t('jobs.generateCv')}
          </SplitButton>
        )}
      </ActionBar>

      <GapSheet
        open={gapSheetOpen}
        onOpenChange={setGapSheetOpen}
        gaps={job.score_gaps || []}
        selectedGaps={selectedGaps}
        onToggleGap={toggleGap}
        instructions={gapInstructions}
        onInstructionsChange={setGapInstructions}
        usage={usage}
        regenerate={hasCv}
        onSubmit={handleGenerateCv}
        busy={cvBusy}
      />
      <CoverLetterSheet
        open={coverLetterOpen}
        onOpenChange={setCoverLetterOpen}
        text={coverLetterText}
        onTextChange={setCoverLetterText}
        pastInstructions={pastInstructions}
        selectedPast={selectedPastInstructions}
        onTogglePast={toggleIn(setSelectedPastInstructions)}
        usage={usage}
        regenerate={Boolean(job.cover_letter_pdf_url)}
        onSubmit={handleGenerateCoverLetter}
        busy={coverLetterBusy}
      />
      <ReferralSheet
        open={referralOpen}
        onOpenChange={setReferralOpen}
        form={referralForm}
        onFormChange={setReferralForm}
        pastInstructions={referralPastInstructions}
        selectedPast={selectedReferralPastInstructions}
        onTogglePast={toggleIn(setSelectedReferralPastInstructions)}
        usage={usage}
        onSubmit={handleGenerateReferral}
        busy={referralBusy}
      />

      <Modal open={undoOpen} onOpenChange={setUndoOpen}>
        <ModalContent>
          <ModalTitle>{t('jobs.undoApplicationTitle')}</ModalTitle>
          <ModalDescription className="text-[15px]">{t('jobs.undoApplicationHint')}</ModalDescription>
          <ModalActions>
            <Button size="lg" disabled={marking} onClick={handleUndoApplicationDone}>
              {t('jobs.undoApplicationConfirm')}
            </Button>
            <Button variant="text" onClick={() => setUndoOpen(false)}>
              {t('jobs.undoApplicationKeep')}
            </Button>
          </ModalActions>
        </ModalContent>
      </Modal>

      <GenerationModal kind={generating} />
      {costDialog}
    </div>
  )
}
