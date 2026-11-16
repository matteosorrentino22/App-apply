import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Archive, Briefcase, Heart, Link as LinkIcon, Plus, Search, SlidersHorizontal } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchJobs,
  archiveJob,
  unarchiveJob,
  favoriteJob,
  unfavoriteJob,
  importJob,
  fetchFilterPresets,
  createFilterPreset,
  deleteFilterPreset,
} from '../api/jobs'
import { fetchSearches } from '../api/searches'
import { ApiError } from '../api/client'
import { formatApiErrorDetail } from '../utils/apiErrors'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Banner } from '@/components/ui/banner'
import { EmptyState } from '@/components/ui/empty-state'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { FilterPill } from '@/components/ui/pill'
import { Modal, ModalActions, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'
import JobCard from '@/components/JobCard'
import CollectJobsSheet, { CollectButton } from '@/components/CollectJobsSheet'
import JobFiltersSheet from '@/components/JobFiltersSheet'
import { APPLICANTS_RANGES, CONTRACT_TYPES, SALARY_VALUES, SCORES, STATUSES } from '../utils/jobFilters'
import ManualJobSheet from '@/components/ManualJobSheet'
import StatsSummary from '@/components/StatsSummary'
import { useCostConfirm } from '@/components/CostConfirmDialog'
import { ActionCostHint } from '@/components/ActionCost'
import { useUsage } from '@/lib/usage'
import { todayInputValue } from '../utils/date'
import { JOB_LIST_SEARCH_STORAGE_KEY } from '../utils/jobListUrl'

const SECTIONS = ['main', 'imported', 'favorites', 'archived']
const RECRUITER_VALUES = ['yes', 'no']
// Parametri che restano nell'URL anche vuoti: "from=" significa "nessun
// limite" ("Tutte le date"), mentre l'assenza significa "oggi" (default).
const KEEP_EMPTY_PARAMS = ['from', 'to']
// Filtri azzerati da "Cancella" / "Azzera filtri": tornano ai valori di
// default (date di oggi, nessun altro filtro). Sezione e ricerca testuale restano.
const FILTER_PARAMS = ['from', 'to', 'location', 'score', 'status', 'search', 'applicants', 'recruiter', 'contract', 'salary']
const EMPTY_ICONS = { main: Briefcase, imported: LinkIcon, favorites: Heart, archived: Archive }

function parseList(value, allowed) {
  const items = value ? value.split(',').filter(Boolean) : []
  return allowed ? items.filter((item) => allowed.includes(item)) : items
}

// Lista Jobs (Sprint 74, mockup `jobs-lista`, `jobs-stats`, `jobs-filtri`,
// `jobs-importati`, `jobs-vuoto`, `save-filter`, `toast-archived`). Stessi
// dati, filtri e azioni di prima; cambia la presentazione: card ridotta e
// cliccabile, statistiche espandibili, filtri in un pannello, raccolta e
// inserimento manuale in pannelli, conferma del costo in una finestra.
export default function JobListPage() {
  const { t } = useLanguage()
  const { user } = useAuth()
  const { usage, refresh: refreshUsage } = useUsage()
  const { confirmCost, costDialog } = useCostConfirm()
  const { showToast } = useToast()

  // Sezione e filtri vivono nella query string (Sprint 68): tornando dal
  // dettaglio di un job (link o back del browser) la lista riparte da dove
  // era, e l'URL è condivisibile. L'ultima query è anche in sessionStorage
  // per il link "Torna alla lista" del dettaglio e degli editor.
  const [searchParams, setSearchParams] = useSearchParams()
  const sectionParam = searchParams.get('section')
  const section = SECTIONS.includes(sectionParam) ? sectionParam : 'main'
  // "Oggi" nel fuso dell'utente, come il filtro lato server (Sprint 70).
  const today = todayInputValue(user?.timezone)
  const dateFrom = searchParams.has('from') ? searchParams.get('from') : today
  const dateTo = searchParams.has('to') ? searchParams.get('to') : today
  const query = searchParams.get('q') || ''
  const location = searchParams.get('location') || ''
  const recruiterParam = searchParams.get('recruiter')
  const recruiterFilter = RECRUITER_VALUES.includes(recruiterParam) ? recruiterParam : 'all'
  // Sprint 82: contratto (multi) e stipendio (tutti / con / senza).
  const salaryParam = searchParams.get('salary')
  const salaryFilter = SALARY_VALUES.includes(salaryParam) ? salaryParam : 'all'
  const contractParam = searchParams.get('contract') || ''
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
  const contractTypes = useMemo(() => parseList(contractParam, CONTRACT_TYPES), [contractParam])

  const [savedSearches, setSavedSearches] = useState([])
  const [queryInput, setQueryInput] = useState(query)
  const [locationInput, setLocationInput] = useState(location)

  const updateParams = useCallback(
    (changes) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current)
          for (const [key, change] of Object.entries(changes)) {
            // Una funzione riceve il valore attuale nell'URL (lista): più
            // clic ravvicinati sulle pillole dei filtri non si annullano a
            // vicenda leggendo uno stato non ancora aggiornato.
            const value = typeof change === 'function' ? change(parseList(next.get(key))) : change
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

  // Filtri attivi contati per gruppo (mockup "2 filtri attivi"): le date
  // contano solo se diverse dal default "oggi".
  const activeFilterCount = [
    dateFrom !== today || dateTo !== today,
    location !== '',
    statuses.length > 0,
    section !== 'imported' && searchFilters.length > 0,
    scores.length > 0,
    applicantsRanges.length > 0,
    recruiterFilter !== 'all',
    contractTypes.length > 0,
    salaryFilter !== 'all',
  ].filter(Boolean).length

  function resetFilters() {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current)
        FILTER_PARAMS.forEach((key) => next.delete(key))
        return next
      },
      { replace: true },
    )
    setLocationInput('')
  }

  const [filterPresets, setFilterPresets] = useState([])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [collectOpen, setCollectOpen] = useState(false)
  const [manualJobOpen, setManualJobOpen] = useState(false)
  const [statsKey, setStatsKey] = useState(0)
  const [showSavePresetDialog, setShowSavePresetDialog] = useState(false)
  const [presetName, setPresetName] = useState('')
  const [savingPreset, setSavingPreset] = useState(false)
  const [presetError, setPresetError] = useState('')

  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [importUrl, setImportUrl] = useState('')
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState('')

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
        contractTypes,
        hasSalary: salaryFilter === 'all' ? undefined : salaryFilter,
      })
      setJobs(data)
    } catch {
      setError(t('jobs.loadError'))
    } finally {
      setLoading(false)
    }
  }, [section, dateFrom, dateTo, scores, statuses, searchFilters, query, location, applicantsRanges, recruiterFilter, contractTypes, salaryFilter, t])

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

  function handleCollected() {
    load()
    setStatsKey((key) => key + 1)
  }

  function openSavePresetDialog() {
    setFiltersOpen(false)
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
        contract_types: contractTypes,
        has_salary: salaryFilter === 'all' ? '' : salaryFilter,
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
      contract: preset.contract_types || [],
      salary: preset.has_salary || '',
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
    if (!(await confirmCost(usage, 'import'))) return
    setImporting(true)
    try {
      await importJob(importUrl)
      setImportUrl('')
      showToast(t('jobs.importSuccess'))
      load()
    } catch (err) {
      setImportError(err instanceof ApiError && err.data?.detail ? err.data.detail : t('common.genericError'))
    } finally {
      setImporting(false)
      refreshUsage()
    }
  }

  const searching = query.length > 0
  const swipeProps =
    section === 'archived'
      ? { onSwipe: handleUnarchive, swipeLabel: t('jobs.unarchive') }
      : { onSwipe: handleArchive, swipeLabel: t('jobs.archive') }
  const importBlocked = usage?.actions?.import?.next_charge === 'blocked'
  const EmptyIcon = EMPTY_ICONS[section]
  const filtered = activeFilterCount > 0 || searching

  return (
    <div className="mx-auto flex max-w-[640px] flex-col gap-4 px-4 pt-6 pb-8 lg:pt-7">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-[28px] leading-tight font-bold tracking-[-0.02em]">{t('list.title')}</h1>
        <CollectButton onClick={() => setCollectOpen(true)} />
      </header>

      <div className="flex gap-2">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            type="search"
            value={queryInput}
            onChange={(event) => handleSearchChange(event.target.value)}
            placeholder={t('jobs.searchPlaceholder')}
            aria-label={t('jobs.searchLabel')}
            className="h-11 pl-11"
          />
        </div>
        <Button
          variant="secondary"
          size="icon"
          onClick={() => setFiltersOpen(true)}
          disabled={searching}
          aria-label={activeFilterCount > 0 ? `${t('jobs.filtersButton')} (${activeFilterCount})` : t('jobs.filtersButton')}
          title={t('jobs.filtersButton')}
          className="relative"
        >
          <SlidersHorizontal className="h-5 w-5" aria-hidden="true" />
          {activeFilterCount > 0 && (
            <span
              aria-hidden="true"
              className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-[11px] font-bold text-primary-foreground"
            >
              {activeFilterCount}
            </span>
          )}
        </Button>
      </div>
      {searching && <p className="text-sm text-muted-foreground">{t('jobs.filtersDisabledWhileSearching')}</p>}

      {section === 'main' && <StatsSummary refreshKey={statsKey} />}

      <div className="flex flex-wrap gap-2">
        {SECTIONS.map((value) => (
          <FilterPill key={value} pressed={section === value} onClick={() => setSection(value)}>
            {t(`jobs.section_${value}`)}
          </FilterPill>
        ))}
      </div>

      {activeFilterCount > 0 && !searching && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-[15px] text-muted-foreground">
            {activeFilterCount === 1 ? t('jobs.activeFiltersOne') : t('jobs.activeFiltersMany').replace('{count}', activeFilterCount)}
          </p>
          <Button variant="text" size="sm" onClick={resetFilters} className="text-[15px] font-bold">
            {t('jobs.clearFilters')}
          </Button>
        </div>
      )}

      {section === 'imported' && (
        <section className="flex flex-col gap-3 rounded-card border border-border bg-card p-4 shadow-card">
          <h2 className="text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{t('jobs.importCardTitle')}</h2>
          {user?.plan === 'pro' ? (
            <form onSubmit={handleImport} className="flex flex-col gap-3">
              <div className="relative">
                <LinkIcon className="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <Input
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  placeholder={t('jobs.importPlaceholder')}
                  aria-label={t('jobs.importPlaceholder')}
                  className="pl-11"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Button type="submit" disabled={importing || importBlocked}>
                  {importing ? t('jobs.importing') : t('jobs.importButton')}
                </Button>
                <Button type="button" variant="secondary" onClick={() => setManualJobOpen(true)}>
                  <Plus className="h-5 w-5" aria-hidden="true" />
                  {t('jobs.addManualJobButton')}
                </Button>
              </div>
              <ActionCostHint usage={usage} action="import" />
              {importError && <Banner variant="error">{importError}</Banner>}
            </form>
          ) : (
            <>
              <p className="flex items-start gap-2 text-sm leading-snug text-muted-foreground">
                <Badge className="mt-px shrink-0">PRO</Badge>
                {t('jobs.importProOnly')}
              </p>
              <Button type="button" variant="secondary" onClick={() => setManualJobOpen(true)} className="self-start">
                <Plus className="h-5 w-5" aria-hidden="true" />
                {t('jobs.addManualJobButton')}
              </Button>
            </>
          )}
        </section>
      )}

      {error && <Banner variant="error">{error}</Banner>}

      {!loading && !error && jobs.length === 0 && (
        <EmptyState
          icon={EmptyIcon}
          description={filtered ? t('jobs.emptyFiltered') : t(`jobs.empty_${section}`)}
          action={
            filtered && activeFilterCount > 0 ? (
              <Button variant="secondary" size="lg" onClick={resetFilters}>
                {t('jobs.resetFilters')}
              </Button>
            ) : section === 'main' && !filtered ? (
              <Button size="lg" onClick={() => setCollectOpen(true)}>
                {t('home.collectButton')}
              </Button>
            ) : null
          }
          className="pt-8"
        />
      )}

      <div className="flex flex-col gap-3.5">
        {jobs.map((job) => (
          <JobCard key={job.id} job={job} onToggleFavorite={handleToggleFavorite} {...swipeProps} />
        ))}
      </div>

      <JobFiltersSheet
        open={filtersOpen}
        onOpenChange={setFiltersOpen}
        section={section}
        filters={{ dateFrom, dateTo, statuses, searchFilters, scores, applicantsRanges, recruiterFilter, contractTypes, salaryFilter }}
        onChange={updateParams}
        locationInput={locationInput}
        onLocationChange={handleLocationChange}
        savedSearches={savedSearches}
        presets={filterPresets}
        onApplyPreset={applyFilterPreset}
        onDeletePreset={handleDeletePreset}
        onSavePreset={openSavePresetDialog}
        onReset={resetFilters}
      />

      <CollectJobsSheet open={collectOpen} onOpenChange={setCollectOpen} onCollected={handleCollected} />

      <ManualJobSheet
        open={manualJobOpen}
        onOpenChange={setManualJobOpen}
        usage={usage}
        confirmCost={confirmCost}
        onCreated={load}
        onDone={refreshUsage}
      />

      <Modal open={showSavePresetDialog} onOpenChange={setShowSavePresetDialog}>
        <ModalContent>
          <ModalTitle>{t('jobs.savePresetDialogTitle')}</ModalTitle>
          <ModalDescription>{t('jobs.savePresetDialogHint')}</ModalDescription>
          <form onSubmit={handleSavePreset} className="flex flex-col gap-3.5">
            <Field label={t('jobs.presetNameLabel')}>
              <Input
                value={presetName}
                onChange={(e) => setPresetName(e.target.value)}
                placeholder={t('jobs.presetNamePlaceholder')}
                autoFocus
                required
              />
            </Field>
            {presetError && <Banner variant="error">{presetError}</Banner>}
            <ModalActions>
              <Button type="submit" size="lg" disabled={savingPreset}>
                {savingPreset ? t('jobs.savingPreset') : t('jobs.savePresetSubmit')}
              </Button>
              <Button type="button" variant="text" onClick={() => setShowSavePresetDialog(false)}>
                {t('jobs.cancel')}
              </Button>
            </ModalActions>
          </form>
        </ModalContent>
      </Modal>

      {costDialog}
    </div>
  )
}
