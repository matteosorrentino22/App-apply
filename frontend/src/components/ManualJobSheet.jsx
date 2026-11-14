import { useState } from 'react'
import { Link as LinkIcon } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { createManualJob } from '../api/jobs'
import { ApiError } from '../api/client'
import { formatApiErrorDetail } from '../utils/apiErrors'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Banner } from '@/components/ui/banner'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import CityOnlyAutocomplete from '@/components/CityOnlyAutocomplete'
import { ActionCostHint } from '@/components/ActionCost'

const EMPTY_MANUAL_JOB = {
  title: '',
  company: '',
  location: '',
  description: '',
  published_at: '',
  apply_url: '',
}

// Inserimento manuale di un job (Sprint 74, mockup `add-manual`,
// `add-manual-cost`, `add-manual-blocked`). Stessi campi, stessa API e
// stessi limiti di prima (Sprint 43/70); in calce il costo della prossima
// richiesta: incluso nel piano, a credito (con conferma in `confirmCost`) o
// bloccato, e allora il pulsante è disattivato.
export default function ManualJobSheet({ open, onOpenChange, usage, confirmCost, onCreated, onDone }) {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const [fields, setFields] = useState(EMPTY_MANUAL_JOB)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const blocked = usage?.actions?.manual_job?.next_charge === 'blocked'

  function handleOpenChange(next) {
    if (creating && !next) return
    if (next) {
      setFields(EMPTY_MANUAL_JOB)
      setError('')
    }
    onOpenChange(next)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!(await confirmCost(usage, 'manual_job'))) return
    setCreating(true)
    try {
      await createManualJob(fields)
      onOpenChange(false)
      showToast(t('jobs.manualJobSuccess'))
      onCreated?.()
    } catch (err) {
      const detail = formatApiErrorDetail(err)
      setError(detail || (err instanceof ApiError && err.data?.detail) || t('jobs.manualJobError'))
    } finally {
      setCreating(false)
      onDone?.()
    }
  }

  const set = (key) => (event) => setFields({ ...fields, [key]: event.target.value })

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent>
        <SheetHeader title={t('jobs.addManualJobDialogTitle')} description={t('jobs.addManualJobDialogHint')} />
        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <SheetBody>
            <Field label={t('jobs.manualJobTitle')}>
              <Input value={fields.title} onChange={set('title')} required />
            </Field>
            <Field label={t('jobs.manualJobCompany')}>
              <Input value={fields.company} onChange={set('company')} required />
            </Field>
            <CityOnlyAutocomplete
              cityId="manual-job-location"
              label={t('jobs.manualJobLocation')}
              city={fields.location}
              onChange={({ city }) => setFields({ ...fields, location: city })}
              required
            />
            <Field label={t('jobs.manualJobDescription')}>
              <Textarea value={fields.description} onChange={set('description')} required className="min-h-32" />
            </Field>
            <Field label={t('jobs.manualJobPublishedAt')}>
              <Input type="datetime-local" value={fields.published_at} onChange={set('published_at')} required />
            </Field>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="manual-job-apply-url">{t('jobs.manualJobApplyUrl')}</Label>
              <div className="relative">
                <LinkIcon className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <Input id="manual-job-apply-url" type="url" value={fields.apply_url} onChange={set('apply_url')} placeholder="https://" className="pl-11" />
              </div>
            </div>
            {error && <Banner variant="error">{error}</Banner>}
          </SheetBody>
          <SheetFooter>
            <ActionCostHint usage={usage} action="manual_job" className="text-center" />
            <Button type="submit" size="lg" disabled={creating || blocked}>
              {creating ? t('jobs.manualJobSubmitting') : t('jobs.manualJobSubmit')}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}
