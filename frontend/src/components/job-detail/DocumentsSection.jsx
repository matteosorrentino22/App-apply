import { Download, FileText, Info, MessageSquare, MoreHorizontal, Pencil, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../../i18n/LanguageContext'
import { Badge } from '@/components/ui/badge'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { DocumentRow } from '@/components/ui/document-row'
import { ExpandableText } from '@/components/ui/expandable-text'
import { Menu } from '@/components/ui/menu'
import { Spinner } from '@/components/ui/spinner'
import { formatShortDate } from '../../utils/date'

// Sezione "Documenti" del dettaglio (Sprint 75, mockup `detail-cv-generato`,
// `detail-docs-pages`, `detail-applied`): CV, cover letter e messaggi di
// networking con apri (scarica), modifica, rigenera / genera. I link di
// download sono gli URL firmati del job (Sprint 66), come prima; gli avvisi
// (più pagine, generato prima dell'editor) sono Banner sotto la riga.

const iconButton =
  'inline-flex h-11 w-11 items-center justify-center rounded-field text-chip-foreground outline-none hover:bg-tint focus-visible:ring-3 focus-visible:ring-ring/30'

function readyStatus(t, readyKey, pageCount) {
  if (!pageCount) return t(readyKey)
  const pages = pageCount === 1 ? t('jobs.docPagesOne') : t('jobs.docPagesMany').replace('{count}', pageCount)
  return `${t(readyKey)} · ${pages}`
}

// Visibile "Genera", nome accessibile completo ("Genera CV", …).
function GenerateButton({ onClick, disabled, label }) {
  const { t } = useLanguage()
  return (
    <Button variant="secondary" className="rounded-full px-3.5" onClick={onClick} disabled={disabled} aria-label={label}>
      <Sparkles className="h-[18px] w-[18px]" aria-hidden="true" />
      {t('jobs.generateShort')}
    </Button>
  )
}

function RowMenu({ label, items }) {
  return (
    <Menu
      label={label}
      items={items}
      trigger={(props) => (
        <button {...props} aria-label={label} className={iconButton}>
          <MoreHorizontal className="h-5 w-5" aria-hidden="true" />
        </button>
      )}
    />
  )
}

function linkedinHref(url) {
  return /^https?:\/\//i.test(url) ? url : `https://${url}`
}

function ReferralMessage({ message, onCopy }) {
  const { t, lang } = useLanguage()
  return (
    <article className="flex flex-col gap-2 rounded-field border border-border p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge variant="neutral">
            {message.channel === 'email' ? t('jobs.referralChannelEmail') : t('jobs.referralChannelLinkedin')}
          </Badge>
          {message.recipient_name ? (
            <span className="min-w-0 break-words text-sm font-semibold text-foreground">{message.recipient_name}</span>
          ) : null}
          <span className="text-xs text-muted-foreground">{formatShortDate(message.generated_at, lang)}</span>
        </div>
        <Button variant="secondary" size="sm" onClick={() => onCopy(message)}>
          {t('jobs.referralCopy')}
        </Button>
      </div>
      {message.recipient_linkedin_url ? (
        <a
          href={linkedinHref(message.recipient_linkedin_url)}
          target="_blank"
          rel="noreferrer"
          className="w-fit text-[13px] font-semibold text-primary hover:underline"
        >
          {t('jobs.referralRecipientLinkedinShort')}
        </a>
      ) : null}
      {message.subject ? <p className="text-sm font-semibold text-foreground">{message.subject}</p> : null}
      <ExpandableText text={message.content} lines={4} className="text-sm text-foreground" />
    </article>
  )
}

export default function DocumentsSection({
  job,
  messages,
  cvBusy,
  coverLetterBusy,
  referralBusy,
  onGenerateCv,
  onGenerateCoverLetter,
  onGenerateReferral,
  onCopyMessage,
}) {
  const { t } = useLanguage()
  const hasCv = Boolean(job.cv_pdf_url)
  const hasCoverLetter = Boolean(job.cover_letter_pdf_url)

  const cvStatus = cvBusy ? (
    <span className="inline-flex items-center gap-1.5">
      <Spinner size={14} label={t('jobs.statusCvGenerating')} />
      {t('jobs.statusCvGenerating')}
    </span>
  ) : hasCv ? (
    readyStatus(t, 'jobs.cvReady', job.cv_page_count)
  ) : (
    t('jobs.cvNotGenerated')
  )

  const coverLetterStatus = coverLetterBusy
    ? t('jobs.generatingCoverLetter')
    : hasCoverLetter
      ? readyStatus(t, 'jobs.coverLetterReady', job.cover_letter_page_count)
      : t('jobs.coverLetterNotGenerated')

  const messagesStatus = referralBusy
    ? t('jobs.generatingReferralMessage')
    : messages.length === 0
      ? t('jobs.messageNotGenerated')
      : messages.length === 1
        ? t('jobs.messagesCountOne')
        : t('jobs.messagesCountMany').replace('{count}', messages.length)

  return (
    <section aria-labelledby="documents-title" className="rounded-card border border-border bg-card p-4 shadow-card">
      <h2 id="documents-title" className="mb-3 text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
        {t('jobs.documentsTitle')}
      </h2>
      <div className="flex flex-col divide-y divide-border">
        <DocumentRow
          data-testid="document-cv"
          icon={FileText}
          title={t('jobs.docCv')}
          status={cvStatus}
          ready={hasCv && !cvBusy}
          actions={
            hasCv ? (
              <>
                {job.cv_editable ? (
                  <Link to={`/jobs/${job.id}/cv-editor`} aria-label={t('cvEditor.editCvButton')} title={t('cvEditor.editCvButton')} className={iconButton}>
                    <Pencil className="h-5 w-5" aria-hidden="true" />
                  </Link>
                ) : null}
                <a
                  href={job.cv_pdf_url}
                  download={job.cv_download_filename}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={t('jobs.downloadCv')}
                  title={t('jobs.downloadCv')}
                  className={iconButton}
                >
                  <Download className="h-5 w-5" aria-hidden="true" />
                </a>
                <RowMenu
                  label={t('jobs.cvActions')}
                  items={[{ key: 'regenerate', label: t('jobs.regenerateCv'), icon: Sparkles, onSelect: onGenerateCv, disabled: cvBusy }]}
                />
              </>
            ) : cvBusy ? null : (
              <GenerateButton onClick={onGenerateCv} label={t('jobs.generateCv')} />
            )
          }
        >
          {hasCv && job.cv_page_count > 1 ? (
            <Banner variant="note" icon={Info}>
              {t('jobs.cvMultiPageWarning').replace('{count}', job.cv_page_count)}
            </Banner>
          ) : null}
          {hasCv && job.cv_editable === false ? (
            <Banner variant="note" icon={Info}>
              {t('jobs.cvNotEditable')}
            </Banner>
          ) : null}
        </DocumentRow>

        <DocumentRow
          data-testid="document-cover-letter"
          icon={FileText}
          title={t('jobs.docCoverLetter')}
          status={coverLetterStatus}
          ready={hasCoverLetter && !coverLetterBusy}
          actions={
            hasCoverLetter ? (
              <>
                {job.cover_letter_editable ? (
                  <Link
                    to={`/jobs/${job.id}/cover-letter-editor`}
                    aria-label={t('coverLetterEditor.editButton')}
                    title={t('coverLetterEditor.editButton')}
                    className={iconButton}
                  >
                    <Pencil className="h-5 w-5" aria-hidden="true" />
                  </Link>
                ) : null}
                <a
                  href={job.cover_letter_pdf_url}
                  download={job.cover_letter_download_filename}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={t('jobs.downloadCoverLetter')}
                  title={t('jobs.downloadCoverLetter')}
                  className={iconButton}
                >
                  <Download className="h-5 w-5" aria-hidden="true" />
                </a>
                <RowMenu
                  label={t('jobs.coverLetterActions')}
                  items={[
                    {
                      key: 'regenerate',
                      label: t('jobs.regenerateCoverLetter'),
                      icon: Sparkles,
                      onSelect: onGenerateCoverLetter,
                      disabled: coverLetterBusy,
                    },
                  ]}
                />
              </>
            ) : (
              <GenerateButton onClick={onGenerateCoverLetter} disabled={coverLetterBusy} label={t('jobs.generateCoverLetter')} />
            )
          }
        >
          {hasCoverLetter && job.cover_letter_page_count > 1 ? (
            <Banner variant="note" icon={Info}>
              {t('jobs.coverLetterMultiPageWarning').replace('{count}', job.cover_letter_page_count)}
            </Banner>
          ) : null}
          {hasCoverLetter && job.cover_letter_editable === false ? (
            <Banner variant="note" icon={Info}>
              {t('jobs.coverLetterNotEditable')}
            </Banner>
          ) : null}
        </DocumentRow>

        <DocumentRow
          data-testid="document-messages"
          icon={MessageSquare}
          title={t('jobs.docMessage')}
          status={messagesStatus}
          ready={messages.length > 0 && !referralBusy}
          actions={
            <GenerateButton onClick={onGenerateReferral} disabled={referralBusy} label={t('jobs.generateReferralMessage')} />
          }
        >
          {messages.length > 0 ? (
            <div className="flex flex-col gap-2.5" aria-label={t('jobs.referralMessagesTitle')} role="group">
              {messages.map((message) => (
                <ReferralMessage key={message.id} message={message} onCopy={onCopyMessage} />
              ))}
            </div>
          ) : null}
        </DocumentRow>
      </div>
    </section>
  )
}
