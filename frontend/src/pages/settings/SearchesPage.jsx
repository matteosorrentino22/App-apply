import { useEffect, useState } from 'react'
import { Info, Lock, Pencil, Plus, Trash2 } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useLanguage } from '../../i18n/LanguageContext'
import { activateSearch, createSearch, deactivateSearch, deleteSearch, fetchSearchLimits, fetchSearches, updateSearch } from '../../api/searches'
import { countryLabel } from '../../utils/countries'
import { ApiError } from '../../api/client'
import { useToast } from '@/components/ToastProvider'
import CityChipsField from '@/components/CityChipsField'
import { SettingsSubpageHeader } from '@/components/settings/SettingsList'
import { ActionBar } from '@/components/ui/action-bar'
import { Badge } from '@/components/ui/badge'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Modal, ModalActions, ModalContent, ModalDescription, ModalTitle } from '@/components/ui/modal'
import { SegmentedControl } from '@/components/ui/segmented'
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import { Spinner } from '@/components/ui/spinner'
import { Switch } from '@/components/ui/switch'

// Ricerche salvate (Sprint 78, mockup `ricerche`, `ricerca-nuova`,
// `delete-search`, `search-deactivated`): stesse operazioni di prima
// (crea, attiva/disattiva, modifica, elimina; limiti del piano dal server),
// in card con interruttore. La nuova ricerca nasce disattivata (§4.2
// funzionali) e il pannello lo dice. Eliminare chiede conferma in una
// finestra (prima era immediato). Sul Free, attivare una ricerca può
// spegnerne un'altra dello stesso tipo: avviso con il nome (Sprint 68).

const EMPTY_SEARCH = { search_type: 'job_role', keywords: '', country: '', cities: [], work_mode: '' }
const WORK_MODES = ['', 'remote', 'hybrid', 'on_site']

function errorText(err, t) {
  return err instanceof ApiError && err.data?.detail ? err.data.detail : t('common.genericError')
}

function SearchSheet({ open, onOpenChange, title, submitLabel, initial, onSubmit, showInactiveHint, limits }) {
  const { t } = useLanguage()
  const { user } = useAuth()
  const isPro = user?.plan === 'pro'
  const maxCities = limits?.max_cities_per_search || (isPro ? 5 : 1)
  const [form, setForm] = useState(initial)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Solo all'apertura: `initial` cambia identità a ogni render del genitore.
  useEffect(() => {
    if (open) {
      setForm(initial)
      setError('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onSubmit(form)
      onOpenChange(false)
    } catch (err) {
      setError(errorText(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader title={title} />
        <form id="search-form" onSubmit={handleSubmit} className="contents">
          <SheetBody className="pt-3">
            {error ? (
              <Banner variant="error">{error}</Banner>
            ) : null}
            <div className="flex flex-col gap-1.5">
              <p className="text-[13px] font-semibold text-label" aria-hidden="true">
                {t('account.searchTypeLabel')}
              </p>
              <SegmentedControl
                name="search-type"
                label={t('account.searchTypeLabel')}
                value={form.search_type}
                onChange={(search_type) => setForm({ ...form, search_type })}
                options={[
                  { value: 'job_role', label: t('account.searchType_job_role') },
                  { value: 'company', label: t('account.searchType_company') },
                ]}
              />
            </div>
            <Field label={t('onboarding.searchKeywords')}>
              <Input
                id="search-keywords"
                value={form.keywords}
                required
                placeholder={t('settings.keywordsPlaceholder')}
                onChange={(event) => setForm({ ...form, keywords: event.target.value })}
              />
            </Field>
            {/* Sprint 84 (A17, A18): paese e città (Free 1, Pro 5, raggio ~40 km),
                modalità di lavoro solo Pro. */}
            <CityChipsField
              idPrefix="search"
              country={form.country}
              onCountryChange={(country) => setForm({ ...form, country, cities: [] })}
              cities={form.cities}
              onCitiesChange={(cities) => setForm({ ...form, cities })}
              maxCities={maxCities}
              hint={
                isPro
                  ? t('searches.citiesHintPro').replace('{used}', limits?.active_cities ?? 0).replace('{max}', limits?.max_active_cities ?? 50)
                  : t('searches.citiesHintFree')
              }
            />
            <div className="flex flex-col gap-1.5">
              <p className="flex items-center gap-2 text-[13px] font-semibold text-label" aria-hidden="true">
                {t('searches.workMode')}
                {isPro ? null : (
                  <Badge variant="primary" className="gap-1 bg-primary text-primary-foreground">
                    <Lock className="h-3 w-3" aria-hidden="true" />
                    PRO
                  </Badge>
                )}
              </p>
              <div className={isPro ? '' : 'pointer-events-none'}>
                <SegmentedControl
                  name="search-work-mode"
                  label={t('searches.workMode')}
                  disabled={!isPro}
                  value={form.work_mode || ''}
                  onChange={(work_mode) => isPro && setForm({ ...form, work_mode })}
                  options={WORK_MODES.map((value) => ({ value, label: t(`searches.workMode_${value || 'any'}`) }))}
                />
              </div>
              <p className="text-[13px] leading-snug text-muted-foreground">
                {isPro ? t('searches.workModeHint') : t('searches.workModeProOnly')}
              </p>
            </div>
            {showInactiveHint ? (
              <Banner variant="note" icon={Info}>
                {t('settings.newSearchInactiveHint')}
              </Banner>
            ) : null}
          </SheetBody>
          <SheetFooter>
            <Button type="submit" size="lg" form="search-form" disabled={busy}>
              {submitLabel}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  )
}

function SearchCard({ search, busy, onToggle, onEdit, onDelete }) {
  const { t, lang } = useLanguage()
  return (
    <article className="flex flex-col gap-3 rounded-card border border-border bg-card p-4 shadow-card" data-testid="search-card">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1.5">
          <span className="flex flex-wrap gap-1.5">
            <Badge variant="neutral" className="text-xs">
              {t(`account.searchType_${search.search_type}`)}
            </Badge>
            {search.work_mode ? (
              <Badge variant="neutral" className="text-xs">
                {t(`searches.workMode_${search.work_mode}`)}
              </Badge>
            ) : null}
          </span>
          <p className="break-words text-[17px] font-bold leading-tight text-foreground">{search.keywords}</p>
          <p className="break-words text-[15px] text-muted-foreground">
            {(search.cities || []).join(', ')} · {countryLabel(search.country, lang)}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Switch
            checked={search.is_active}
            disabled={busy}
            label={t('settings.searchToggleLabel').replace('{name}', search.keywords)}
            onCheckedChange={() => onToggle(search)}
          />
          <span className="text-xs font-semibold text-muted-foreground">
            {search.is_active ? t('account.activeBadge') : t('settings.searchInactive')}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <Button variant="secondary" disabled={busy} onClick={() => onEdit(search)}>
          <Pencil className="h-4 w-4" aria-hidden="true" />
          {t('account.edit')}
        </Button>
        <Button variant="secondary" className="text-destructive-text" disabled={busy} onClick={() => onDelete(search)}>
          <Trash2 className="h-4 w-4" aria-hidden="true" />
          {t('account.delete')}
        </Button>
      </div>
    </article>
  )
}

export default function SearchesPage() {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const [searches, setSearches] = useState(null)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [limits, setLimits] = useState(null)

  function refreshLimits() {
    fetchSearchLimits().then(setLimits).catch(() => {})
  }

  useEffect(() => {
    refreshLimits()
    fetchSearches()
      .then(setSearches)
      .catch(() => {
        setSearches([])
        showToast(t('common.genericError'))
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function applySearchUpdate(result) {
    const previous = result.deactivated_previous
    setSearches((current) =>
      current.map((s) => (s.id === result.id ? result : previous && s.id === previous.id ? previous : s)),
    )
    if (previous) {
      showToast(t('account.searchDeactivatedToast').replace('{name}', previous.keywords), {
        action: { label: t('settings.ok'), onClick: () => {} },
        duration: 8000,
      })
    }
  }

  async function handleToggle(search) {
    setBusyId(search.id)
    setError('')
    try {
      if (search.is_active) {
        const updated = await deactivateSearch(search.id)
        setSearches((current) => current.map((s) => (s.id === updated.id ? updated : s)))
      } else {
        applySearchUpdate(await activateSearch(search.id))
      }
    } catch (err) {
      setError(errorText(err, t))
    } finally {
      setBusyId(null)
      refreshLimits()
    }
  }

  async function handleCreate(form) {
    const created = await createSearch(form)
    setSearches((current) => [...current, created])
    showToast(t('settings.searchCreatedToast'))
    refreshLimits()
  }

  async function handleUpdate(form) {
    applySearchUpdate(await updateSearch(editing.id, form))
    refreshLimits()
  }

  async function handleDelete() {
    const search = deleting
    setBusyId(search.id)
    try {
      await deleteSearch(search.id)
      setSearches((current) => current.filter((s) => s.id !== search.id))
      setDeleting(null)
      refreshLimits()
    } catch {
      showToast(t('common.genericError'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 pb-6 pt-3 lg:pt-6">
      <SettingsSubpageHeader title={t('account.searchesTitle')} description={t('searches.pageHint')} />
      {limits?.max_active_cities ? (
        <div className="flex flex-col gap-1.5" data-testid="active-cities">
          <div className="flex items-baseline justify-between text-[15px]">
            <span className="font-semibold text-foreground">{t('searches.activeCities')}</span>
            <span className="tabular-nums text-muted-foreground">
              {t('searches.activeCitiesCount').replace('{used}', limits.active_cities).replace('{max}', limits.max_active_cities)}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-secondary" aria-hidden="true">
            <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, (100 * limits.active_cities) / limits.max_active_cities)}%` }} />
          </div>
        </div>
      ) : null}
      {error ? <Banner variant="error">{error}</Banner> : null}
      {searches == null ? (
        <div className="flex justify-center py-10">
          <Spinner size={28} />
        </div>
      ) : searches.length === 0 ? (
        <EmptyState icon={Plus} title={t('account.noSearches')} description={t('settings.noSearchesHint')} />
      ) : (
        searches.map((search) => (
          <SearchCard
            key={search.id}
            search={search}
            busy={busyId === search.id}
            onToggle={handleToggle}
            onEdit={setEditing}
            onDelete={setDeleting}
          />
        ))
      )}

      {/* Sprint 81: sopra la barra di tab, che resta visibile (mockup `ricerche`). */}
      <ActionBar stacked>
        <Button size="lg" onClick={() => setCreating(true)}>
          <Plus className="h-5 w-5" aria-hidden="true" />
          {t('account.newSearch')}
        </Button>
      </ActionBar>

      <SearchSheet
        open={creating}
        onOpenChange={setCreating}
        title={t('account.newSearch')}
        submitLabel={t('account.addSearch')}
        initial={EMPTY_SEARCH}
        onSubmit={handleCreate}
        limits={limits}
        showInactiveHint
      />
      <SearchSheet
        open={editing != null}
        onOpenChange={(open) => !open && setEditing(null)}
        title={t('settings.editSearchTitle')}
        submitLabel={t('account.save')}
        initial={
          editing
            ? {
                search_type: editing.search_type,
                keywords: editing.keywords,
                country: editing.country,
                cities: editing.cities || [],
                work_mode: editing.work_mode || '',
              }
            : EMPTY_SEARCH
        }
        onSubmit={handleUpdate}
        limits={limits}
      />
      <Modal open={deleting != null} onOpenChange={(open) => !open && setDeleting(null)}>
        <ModalContent>
          <ModalTitle>{t('settings.deleteSearchTitle')}</ModalTitle>
          <ModalDescription className="text-[15px]">
            {t('settings.deleteSearchBody').replace('{name}', deleting?.keywords || '')}
          </ModalDescription>
          <ModalActions>
            <Button variant="destructive" size="lg" disabled={busyId != null} onClick={handleDelete}>
              {t('account.delete')}
            </Button>
            <Button variant="text" onClick={() => setDeleting(null)}>
              {t('account.cancel')}
            </Button>
          </ModalActions>
        </ModalContent>
      </Modal>
    </div>
  )
}
