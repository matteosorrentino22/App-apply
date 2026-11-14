import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { X } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchJobs,
  fetchJob,
  generateCv,
  archiveJob,
  unarchiveJob,
  favoriteJob,
  unfavoriteJob,
  importJob,
  createManualJob,
  fetchFilterPresets,
  createFilterPreset,
  deleteFilterPreset,
} from '../api/jobs'
import { fetchSearches } from '../api/searches'
import { ApiError } from '../api/client'
import { formatApiErrorDetail } from '../utils/apiErrors'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import JobCard from '@/components/JobCard'
import MultiSelectFilter from '@/components/MultiSelectFilter'
import CityOnlyAutocomplete from '@/components/CityOnlyAutocomplete'
import { todayInputValue } from '../utils/date'
import { JOB_LIST_SEARCH_STORAGE_KEY } from '../utils/jobListUrl'

const EMPTY_MANUAL_JOB = {
  title: '',
  company: '',
  location: '',
  description: '',
  published_at: '',
  apply_url: '',
}

const SECTIONS = ['main', 'imported', 'favorites', 'archived']
const SCORES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
const STATUSES = ['new', 'cv_generated', 'application_done']
const APPLICANTS_RANGES = ['under_25', '25_50', '51_100', '101_200', 'over_200']
const RECRUITER_VALUES = ['yes', 'no']
// Parametri che restano nell'URL anche vuoti: "from=" significa "nessun
// limite" (pulsante "Tutto"), mentre l'assenza significa "oggi" (default).
const KEEP_EMPTY_PARAMS = ['from', 'to']

function parseList(value, allowed) {
  const items = value ? value.split(',').filter(Boolean) : []
  return allowed ? items.filter((item) => allowed.includes(item)) : items
}

export default function JobListPage() {
  const { t } = useLanguage()
  const { user, logout } = useAuth()
  const { showToast } = useToast()

  // Sezione e filtri vivono nella query string (Sprint 68): tornando dal
  // dettaglio di un job (link o back del browser) la lista riparte da dove
  // era, e l'URL è condivisibile. L'ultima query è anche in sessionStorage
  // per il link "Torna alla lista" del dettaglio e degli editor.
  const [searchParams, setSearchParams] = useSearchParams()
  const sectionParam = searchParams.get('section')
  const section = SECTIONS.includes(sectionParam) ? sectionParam : 'main'
  const dateFrom = searchParams.has('from') ? searchParams.get('from') : todayInputValue()
  const dateTo = searchParams.has('to') ? searchParams.get('to') : todayInputValue()
  const query = searchParams.get('q') || ''
  const location = searchParams.get('location') || ''
  const recruiterParam = searchParams.get('recruiter')
  const recruiterFilter = RECRUITER_VALUES.includes(recruiterParam) ? recruiterParam : 'all'
  const scoreParam = searchParams.get('score') || ''
  const statusParam = searchParams.get('status') || ''
  const searchParam = searchParams.get('search') || ''
  const applicantsParam = searchParams.get('applicants') || ''
  const scores = useMemo(
    () => parseList(scoreParam).map(Number).filter((value) => SCORES.includes(value)),
    [scoreParam],
  )
  const statuses = useMemo(() => parseList(statusParam, STATUSES), [statusParam])
  const searchFilters = useMemo(() => parseList(searchParam), [searchParam])
  const applicantsRanges = useMemo(() => parseList(applicantsParam, APPLICANTS_RANGES), [applicantsParam])

  const [savedSearches, setSavedSearches] = useState([])
  const [queryInput, setQueryInput] = useState(query)
  const [locationInput, setLocationInput] = useState(location)

  const updateParams = useCallback(
    (changes) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current)
          for (const [key, value] of Object.entries(changes)) {
            const text = Array.isArray(value) ? value.join(',') : (value ?? '')
            if (text === '' && !KEEP_EMPTY_PARAMS.includes(key)) {
              next.delete(key)
            } else {
              next.set(key, text)
            }
          }
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const listSearch = searchParams.toString()
  useEffect(() => {
    sessionStorage.setItem(JOB_LIST_SEARCH_STORAGE_KEY, listSearch ? `?${listSearch}` : '')
  }, [listSearch])

  const setSection = (value) => updateParams({ section: value === 'main' ? '' : value })
  const setDateFrom = (value) => updateParams({ from: value })
  const setDateTo = (value) => updateParams({ to: value })
  const setScores = (value) => updateParams({ score: value })
  const setStatuses = (value) => updateParams({ status: value })
  const setSearchFilters = (value) => updateParams({ search: value })
  const setApplicantsRanges = (value) => updateParams({ applicants: value })
  const setRecruiterFilter = (value) => updateParams({ recruiter: value === 'all' ? '' : value })

  const [filterPresets, setFilterPresets] = useState([])
  const [showSavePresetDialog, setShowSavePresetDialog] = useState(false)
  const [presetName, setPresetName] = useState('')
  const [savingPreset, setSavingPreset] = useState(false)
  const [presetError, setPresetError] = useState('')

  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generatingIds, setGeneratingIds] = useState(() => new Set())

  const [importUrl, setImportUrl] = useState('')
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState('')

  const [showManualJobDialog, setShowManualJobDialog] = useState(false)
  const [manualJobFields, setManualJobFields] = useState(EMPTY_MANUAL_JOB)
  const [creatingManualJob, setCreatingManualJob] = useState(false)
  const [manualJobError, setManualJobError] = useState('')

  const debounceRef = useRef(null)
  const locationDebounceRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      // Il filtro ricerca non ha senso per i job importati (nessuno ha una
      // ricerca di provenienza): ignorato lato client per questa sezione,
      // anche se resta selezionato per quando l'utente torna su Raccolti/
      // Archiviati.
      const searchIds = section === 'imported' ? undefined : searchFilters
      const data = await fetchJobs({
        section,
        dateFrom,
        dateTo,
        scores,
        statuses,
        q: query,
        searchIds,
        location,
        applicantsRanges,
        hasRecruiter: recruiterFilter === 'all' ? undefined : recruiterFilter,
      })
      setJobs(data)
    } catch {
      setError(t('jobs.loadError'))
    } finally {
      setLoading(false)
    }
  }, [
    section,
    dateFrom,
    dateTo,
    scores,
    statuses,
    searchFilters,
    query,
    location,
    applicantsRanges,
    recruiterFilter,
    t,
  ])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    fetchSearches()
      .then(setSavedSearches)
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchFilterPresets()
      .then(setFilterPresets)
      .catch(() => {})
  }, [])

  function openSavePresetDialog() {
    setPresetName('')
    setPresetError('')
    setShowSavePresetDialog(true)
  }

  async function handleSavePreset(event) {
    event.preventDefault()
    setPresetError('')
    setSavingPreset(true)
    try {
      const created = await createFilterPreset({
        name: presetName,
        scores,
        statuses,
        // Nella sezione Importati il filtro "Ricerca" è nascosto e ignorato:
        // non va salvato, altrimenti tornerebbe attivo applicando il preset
        // da un'altra sezione.
        search_ids: section === 'imported' ? [] : searchFilters,
        location,
        applicants_ranges: applicantsRanges,
        has_recruiter: recruiterFilter === 'all' ? '' : recruiterFilter,
      })
      setFilterPresets((current) => [...current, created])
      setShowSavePresetDialog(false)
    } catch (err) {
      const detail = formatApiErrorDetail(err)
      setPresetError(detail || (err instanceof ApiError && err.data?.detail) || t('jobs.savePresetError'))
    } finally {
      setSavingPreset(false)
    }
  }

  // Copia i valori del preset nei filtri "di questo momento": l'utente può
  // poi modificarli liberamente senza toccare il preset salvato (nessun
  // legame persistente tra i due dopo l'applicazione). Mai le date, che il
  // preset non contiene.
  function applyFilterPreset(preset) {
    updateParams({
      score: preset.scores || [],
      status: preset.statuses || [],
      search: preset.search_ids || [],
      location: preset.location || '',
      applicants: preset.applicants_ranges || [],
      recruiter: preset.has_recruiter || '',
    })
    setLocationInput(preset.location || '')
  }

  // Rimozione ottimistica, ma se l'API fallisce la pillola torna al suo
  // posto (ordine di creazione, come la lista del server) con un messaggio.
  async function handleDeletePreset(preset) {
    setFilterPresets((current) => current.filter((item) => item.id !== preset.id))
    try {
      await deleteFilterPreset(preset.id)
    } catch {
      setFilterPresets((current) =>
        [...current, preset].sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : a.id - b.id)),
      )
      showToast(t('jobs.deletePresetError'))
    }
  }

  function handleSearchChange(value) {
    setQueryInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => updateParams({ q: value }), 300)
  }

  function handleLocationChange(value) {
    setLocationInput(value)
    if (locationDebounceRef.current) clearTimeout(locationDebounceRef.current)
    locationDebounceRef.current = setTimeout(() => updateParams({ location: value }), 300)
  }

  function resetDateRange() {
    updateParams({ from: '', to: '' })
  }

  function toggleValue(list, setList, value) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  }

  async function handleGenerateCv(job) {
    setGeneratingIds((current) => new Set(current).add(job.id))
    try {
      await generateCv(job.id)
      const updated = await fetchJob(job.id)
      setJobs((current) => current.map((j) => (j.id === job.id ? updated : j)))
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Il backend distingue più cause dietro lo stesso 409 (concorrenza,
        // profilo incompleto, massimale/credito esaurito): il messaggio
        // esatto arriva in `detail` (stesso fix di JobDetailPage, Sprint 30).
        showToast(err.data?.detail || t('jobs.generationConflict'))
      } else {
        showToast(t('jobs.generationFailed'))
      }
    } finally {
      setGeneratingIds((current) => {
        const next = new Set(current)
        next.delete(job.id)
        return next
      })
    }
  }

  async function handleArchive(job) {
    setJobs((current) => current.filter((j) => j.id !== job.id))
    await archiveJob(job.id)
    showToast(t('jobs.archivedToast'), {
      action: {
        label: t('jobs.undo'),
        onClick: async () => {
          await unarchiveJob(job.id)
          load()
        },
      },
    })
  }

  async function handleUnarchive(job) {
    setJobs((current) => current.filter((j) => j.id !== job.id))
    await unarchiveJob(job.id)
    showToast(t('jobs.unarchivedToast'))
  }

  async function handleToggleFavorite(job) {
    const nextFavorite = !job.is_favorite
    if (section === 'favorites' && !nextFavorite) {
      setJobs((current) => current.filter((j) => j.id !== job.id))
    } else {
      setJobs((current) => current.map((j) => (j.id === job.id ? { ...j, is_favorite: nextFavorite } : j)))
    }
    if (nextFavorite) {
      await favoriteJob(job.id)
    } else {
      await unfavoriteJob(job.id)
    }
  }

  async function handleImport(event) {
    event.preventDefault()
    setImportError('')
    setImporting(true)
    try {
      await importJob(importUrl)
      setImportUrl('')
      showToast(t('jobs.importSuccess'))
      load()
    } catch (err) {
      setImportError(
        err instanceof ApiError && err.data?.detail ? err.data.detail : t('common.genericError'),
      )
    } finally {
      setImporting(false)
    }
  }

  function openManualJobDialog() {
    setManualJobFields(EMPTY_MANUAL_JOB)
    setManualJobError('')
    setShowManualJobDialog(true)
  }

  async function handleCreateManualJob(event) {
    event.preventDefault()
    setManualJobError('')
    setCreatingManualJob(true)
    try {
      await createManualJob(manualJobFields)
      setShowManualJobDialog(false)
      showToast(t('jobs.manualJobSuccess'))
      load()
    } catch (err) {
      const detail = formatApiErrorDetail(err)
      setManualJobError(
        detail || (err instanceof ApiError && err.data?.detail) || t('jobs.manualJobError'),
      )
    } finally {
      setCreatingManualJob(false)
    }
  }

  const searching = query.length > 0
  const swipeProps =
    section === 'archived'
      ? { onSwipe: handleUnarchive, swipeLabel: t('jobs.unarchive') }
      : { onSwipe: handleArchive, swipeLabel: t('jobs.archive') }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-4 py-10">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">{t('list.title')}</h1>
        <Button variant="secondary" size="sm" onClick={logout}>
          {t('list.logout')}
        </Button>
      </header>

      <div className="flex gap-2">
        {SECTIONS.map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setSection(value)}
            className={
              'rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ' +
              (section === value
                ? 'bg-primary text-primary-foreground'
                : 'bg-secondary text-muted-foreground hover:text-foreground')
            }
          >
            {t(`jobs.section_${value}`)}
          </button>
        ))}
      </div>

      {section === 'imported' && (
        <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
          {user?.plan === 'pro' ? (
            <form onSubmit={handleImport} className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                <Input
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  placeholder={t('jobs.importPlaceholder')}
                  aria-label={t('jobs.importPlaceholder')}
                  className="min-w-64 flex-1"
                  required
                />
                <Button type="submit" disabled={importing}>
                  {importing ? t('jobs.importing') : t('jobs.importButton')}
                </Button>
              </div>
              {importError && (
                <p role="alert" className="text-sm text-destructive">
                  {importError}
                </p>
              )}
            </form>
          ) : (
            <p className="text-sm text-muted-foreground">{t('jobs.importProOnly')}</p>
          )}

          <Button type="button" variant="secondary" size="sm" onClick={openManualJobDialog} className="w-fit">
            {t('jobs.addManualJobButton')}
          </Button>
        </div>
      )}

      <Input
        value={queryInput}
        onChange={(event) => handleSearchChange(event.target.value)}
        placeholder={t('jobs.searchPlaceholder')}
        aria-label={t('jobs.searchPlaceholder')}
      />

      <div className={'flex flex-wrap items-center gap-4' + (searching ? ' opacity-40' : '')}>
        <div className="flex items-center gap-1.5">
          <Label htmlFor="date-from" className="text-xs font-medium text-muted-foreground">
            {t('jobs.dateFromLabel')}
          </Label>
          <Input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
            disabled={searching}
            className="w-36"
          />
          <Label htmlFor="date-to" className="text-xs font-medium text-muted-foreground">
            {t('jobs.dateToLabel')}
          </Label>
          <Input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            disabled={searching}
            className="w-36"
          />
          {(dateFrom || dateTo) && (
            <button
              type="button"
              onClick={resetDateRange}
              disabled={searching}
              className="text-xs font-medium text-muted-foreground hover:text-foreground hover:underline"
            >
              {t('jobs.dateRangeAll')}
            </button>
          )}
        </div>

        <Input
          value={locationInput}
          onChange={(event) => handleLocationChange(event.target.value)}
          placeholder={t('jobs.locationFilterPlaceholder')}
          aria-label={t('jobs.locationFilterPlaceholder')}
          disabled={searching}
          className="w-48"
        />

        {section !== 'imported' && (
          <MultiSelectFilter
            label={t('jobs.searchFilterLabel')}
            layout="list"
            options={[
              ...savedSearches.map((search) => ({
                value: String(search.id),
                label:
                  `${t(`account.searchType_${search.search_type}`)}: ${search.keywords} — ` +
                  `${search.city}, ${search.country}`,
              })),
              { value: 'none', label: t('jobs.searchFilter_none') },
            ]}
            selected={searchFilters}
            onToggle={(value) => toggleValue(searchFilters, setSearchFilters, value)}
            disabled={searching}
          />
        )}

        <MultiSelectFilter
          label={t('jobs.scoreLabel')}
          options={SCORES.map((value) => ({ value, label: String(value) }))}
          selected={scores}
          onToggle={(value) => toggleValue(scores, setScores, value)}
          disabled={searching}
        />

        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">{t('jobs.statusLabel')}</span>
          {STATUSES.map((value) => (
            <button
              key={value}
              type="button"
              disabled={searching}
              onClick={() => toggleValue(statuses, setStatuses, value)}
              aria-pressed={statuses.includes(value)}
              className={
                'rounded-full px-2.5 py-1 text-xs font-medium transition-colors ' +
                (statuses.includes(value)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground hover:text-foreground')
              }
            >
              {t(`jobs.status_${value}`)}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">{t('jobs.applicantsLabel')}</span>
          {APPLICANTS_RANGES.map((value) => (
            <button
              key={value}
              type="button"
              disabled={searching}
              onClick={() => toggleValue(applicantsRanges, setApplicantsRanges, value)}
              aria-pressed={applicantsRanges.includes(value)}
              className={
                'rounded-full px-2.5 py-1 text-xs font-medium transition-colors ' +
                (applicantsRanges.includes(value)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground hover:text-foreground')
              }
            >
              {t(`jobs.applicants_${value}`)}
            </button>
          ))}
        </div>

        <Select value={recruiterFilter} onValueChange={setRecruiterFilter} disabled={searching}>
          <SelectTrigger aria-label={t('jobs.recruiterFilterLabel')} className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('jobs.recruiterFilter_all')}</SelectItem>
            <SelectItem value="yes">{t('jobs.recruiterFilter_yes')}</SelectItem>
            <SelectItem value="no">{t('jobs.recruiterFilter_no')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className={'flex flex-wrap items-center gap-2' + (searching ? ' opacity-40' : '')}>
        {filterPresets.map((preset) => (
          <span
            key={preset.id}
            className="flex items-center gap-1 rounded-full bg-secondary pl-2.5 pr-1.5 py-1 text-xs font-medium text-muted-foreground"
          >
            <button
              type="button"
              disabled={searching}
              onClick={() => applyFilterPreset(preset)}
              className="hover:text-foreground"
            >
              {preset.name}
            </button>
            <button
              type="button"
              disabled={searching}
              onClick={() => handleDeletePreset(preset)}
              aria-label={t('jobs.deletePreset')}
              className="text-muted-foreground/60 hover:text-destructive"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <Button type="button" variant="secondary" size="sm" disabled={searching} onClick={openSavePresetDialog}>
          {t('jobs.savePresetButton')}
        </Button>
      </div>
      {searching && <p className="text-xs text-muted-foreground">{t('jobs.filtersDisabledWhileSearching')}</p>}

      {error && (
        <p role="alert" className="rounded-md bg-destructive-soft px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {!loading && !error && jobs.length === 0 && (
        <p className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          {t(`jobs.empty_${section}`)}
        </p>
      )}

      <div className="flex flex-col gap-3">
        {jobs.map((job) => (
          <JobCard
            key={job.id}
            job={job}
            onGenerateCv={handleGenerateCv}
            onToggleFavorite={handleToggleFavorite}
            generating={generatingIds.has(job.id)}
            {...swipeProps}
          />
        ))}
      </div>

      <Dialog open={showManualJobDialog} onOpenChange={setShowManualJobDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('jobs.addManualJobDialogTitle')}</DialogTitle>
            <DialogDescription>{t('jobs.addManualJobDialogHint')}</DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateManualJob} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="manual-job-title">{t('jobs.manualJobTitle')}</Label>
              <Input
                id="manual-job-title"
                value={manualJobFields.title}
                onChange={(e) => setManualJobFields({ ...manualJobFields, title: e.target.value })}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="manual-job-company">{t('jobs.manualJobCompany')}</Label>
              <Input
                id="manual-job-company"
                value={manualJobFields.company}
                onChange={(e) => setManualJobFields({ ...manualJobFields, company: e.target.value })}
                required
              />
            </div>
            <CityOnlyAutocomplete
              cityId="manual-job-location"
              label={t('jobs.manualJobLocation')}
              city={manualJobFields.location}
              onChange={({ city }) => setManualJobFields({ ...manualJobFields, location: city })}
              required
            />
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="manual-job-description">{t('jobs.manualJobDescription')}</Label>
              <Textarea
                id="manual-job-description"
                value={manualJobFields.description}
                onChange={(e) =>
                  setManualJobFields({ ...manualJobFields, description: e.target.value })
                }
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="manual-job-published-at">{t('jobs.manualJobPublishedAt')}</Label>
              <Input
                id="manual-job-published-at"
                type="datetime-local"
                value={manualJobFields.published_at}
                onChange={(e) =>
                  setManualJobFields({ ...manualJobFields, published_at: e.target.value })
                }
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="manual-job-apply-url">{t('jobs.manualJobApplyUrl')}</Label>
              <Input
                id="manual-job-apply-url"
                type="url"
                value={manualJobFields.apply_url}
                onChange={(e) =>
                  setManualJobFields({ ...manualJobFields, apply_url: e.target.value })
                }
              />
            </div>

            {manualJobError && (
              <p role="alert" className="text-sm text-destructive">
                {manualJobError}
              </p>
            )}

            <DialogFooter>
              <Button type="button" variant="secondary" onClick={() => setShowManualJobDialog(false)}>
                {t('jobs.cancel')}
              </Button>
              <Button type="submit" disabled={creatingManualJob}>
                {creatingManualJob ? t('jobs.manualJobSubmitting') : t('jobs.manualJobSubmit')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={showSavePresetDialog} onOpenChange={setShowSavePresetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('jobs.savePresetDialogTitle')}</DialogTitle>
            <DialogDescription>{t('jobs.savePresetDialogHint')}</DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSavePreset} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="preset-name">{t('jobs.presetNameLabel')}</Label>
              <Input
                id="preset-name"
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                autoFocus
                required
              />
            </div>

            {presetError && (
              <p role="alert" className="text-sm text-destructive">
                {presetError}
              </p>
            )}

            <DialogFooter>
              <Button type="button" variant="secondary" onClick={() => setShowSavePresetDialog(false)}>
                {t('jobs.cancel')}
              </Button>
              <Button type="submit" disabled={savingPreset}>
                {savingPreset ? t('jobs.savingPreset') : t('jobs.savePresetSubmit')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
