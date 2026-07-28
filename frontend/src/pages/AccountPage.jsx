import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { updateMe } from '../api/auth'
import {
  fetchSearches,
  createSearch,
  updateSearch,
  deleteSearch,
  activateSearch,
  deactivateSearch,
} from '../api/searches'
import { fetchVapidPublicKey, registerPushSubscription } from '../api/notifications'
import { isPushSupported, isIOS, isStandalone, subscribeToPush } from '../lib/push'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import CityAutocomplete from '@/components/CityAutocomplete'
import { SUPPORTED_LANGUAGES } from '../i18n/translations'

const EMPTY_SEARCH = { keywords: '', city: '', country: '' }

function formatCredit(value) {
  const amount = Number(value ?? 0)
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(amount)
}

export default function AccountPage() {
  const { t, lang, setLang } = useLanguage()
  const { user, refreshUser } = useAuth()
  const { showToast } = useToast()

  const [searches, setSearches] = useState([])
  const [loadingSearches, setLoadingSearches] = useState(true)
  const [newSearch, setNewSearch] = useState(EMPTY_SEARCH)
  const [searchError, setSearchError] = useState('')
  const [busySearchId, setBusySearchId] = useState(null)
  const [editingSearchId, setEditingSearchId] = useState(null)
  const [editedSearch, setEditedSearch] = useState(EMPTY_SEARCH)

  const [notificationStatus, setNotificationStatus] = useState('idle')

  // Stato locale ottimistico per le impostazioni: senza, il controllo (radio/
  // checkbox) resterebbe visivamente fermo fino al giro di rete completo di
  // PATCH + refreshUser, sembrando "non rispondere" al click.
  const [cvLanguageMode, setCvLanguageMode] = useState(user?.cv_language_mode)
  const [cvIncludePhoto, setCvIncludePhoto] = useState(user?.cv_include_photo ?? false)

  useEffect(() => {
    loadSearches()
    checkExistingSubscription()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadSearches() {
    setLoadingSearches(true)
    try {
      setSearches(await fetchSearches())
    } catch {
      showToast(t('common.genericError'))
    } finally {
      setLoadingSearches(false)
    }
  }

  async function checkExistingSubscription() {
    if (!isPushSupported() || !navigator.serviceWorker.controller) return
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    if (subscription) setNotificationStatus('granted')
  }

  async function handleCreateSearch(event) {
    event.preventDefault()
    setSearchError('')
    try {
      const created = await createSearch(newSearch)
      setSearches((current) => [...current, created])
      setNewSearch(EMPTY_SEARCH)
    } catch (err) {
      setSearchError(
        err instanceof ApiError && err.data?.detail ? err.data.detail : t('common.genericError'),
      )
    }
  }

  async function handleToggleActive(search) {
    setBusySearchId(search.id)
    setSearchError('')
    try {
      if (search.is_active) {
        const updated = await deactivateSearch(search.id)
        setSearches((current) => current.map((s) => (s.id === updated.id ? updated : s)))
      } else {
        const result = await activateSearch(search.id)
        setSearches((current) =>
          current.map((s) => {
            if (s.id === result.id) return result
            if (result.deactivated_previous && s.id === result.deactivated_previous.id) {
              return result.deactivated_previous
            }
            return s
          }),
        )
      }
    } catch (err) {
      setSearchError(
        err instanceof ApiError && err.data?.detail ? err.data.detail : t('common.genericError'),
      )
    } finally {
      setBusySearchId(null)
    }
  }

  function handleStartEdit(search) {
    setEditingSearchId(search.id)
    setEditedSearch({ keywords: search.keywords, city: search.city, country: search.country })
    setSearchError('')
  }

  function handleCancelEdit() {
    setEditingSearchId(null)
    setEditedSearch(EMPTY_SEARCH)
  }

  async function handleSaveEdit(event) {
    event.preventDefault()
    setBusySearchId(editingSearchId)
    setSearchError('')
    try {
      const updated = await updateSearch(editingSearchId, editedSearch)
      setSearches((current) => current.map((s) => (s.id === updated.id ? updated : s)))
      setEditingSearchId(null)
    } catch (err) {
      setSearchError(
        err instanceof ApiError && err.data?.detail ? err.data.detail : t('common.genericError'),
      )
    } finally {
      setBusySearchId(null)
    }
  }

  async function handleDeleteSearch(search) {
    setBusySearchId(search.id)
    try {
      await deleteSearch(search.id)
      setSearches((current) => current.filter((s) => s.id !== search.id))
    } catch {
      showToast(t('common.genericError'))
    } finally {
      setBusySearchId(null)
    }
  }

  async function handleSettingChange(patch) {
    try {
      await updateMe(patch)
      await refreshUser()
      showToast(t('account.settingsSaved'))
    } catch {
      showToast(t('common.genericError'))
    }
  }

  async function handleEnableNotifications() {
    setNotificationStatus('requesting')
    try {
      const vapidPublicKey = await fetchVapidPublicKey()
      const result = await subscribeToPush(vapidPublicKey)
      if (result.status === 'granted' && result.subscription) {
        await registerPushSubscription(result.subscription)
        setNotificationStatus('granted')
      } else {
        setNotificationStatus(result.status)
      }
    } catch {
      setNotificationStatus('error')
    }
  }

  if (!user) return null

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <div>
        <Link to="/list" className="text-sm font-medium text-primary hover:underline">
          ← {t('jobs.backToList')}
        </Link>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">{t('account.title')}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('account.planTitle')}</CardTitle>
          <CardDescription>{t('account.creditHint')}</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center gap-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('account.planTitle')}
            </p>
            <Badge className="mt-1" variant="primary">
              {t(`account.plan_${user.plan}`)}
            </Badge>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('account.creditBalance')}
            </p>
            <p className="mt-1 text-lg font-semibold tabular-nums">{formatCredit(user.extra_credit)}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('account.searchesTitle')}</CardTitle>
          <CardDescription>{t('account.searchesHint')}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {searchError && (
            <p role="alert" className="text-sm text-destructive">
              {searchError}
            </p>
          )}

          {!loadingSearches && searches.length === 0 && (
            <p className="text-sm text-muted-foreground">{t('account.noSearches')}</p>
          )}

          {searches.map((search) =>
            editingSearchId === search.id ? (
              <form
                key={search.id}
                onSubmit={handleSaveEdit}
                className="flex flex-col gap-3 rounded-lg border border-border p-3"
              >
                <div className="flex flex-wrap gap-3">
                  <div className="flex min-w-32 flex-1 flex-col gap-1.5">
                    <Label htmlFor={`edit-search-keywords-${search.id}`}>
                      {t('onboarding.searchKeywords')}
                    </Label>
                    <Input
                      id={`edit-search-keywords-${search.id}`}
                      value={editedSearch.keywords}
                      onChange={(e) =>
                        setEditedSearch({ ...editedSearch, keywords: e.target.value })
                      }
                      required
                    />
                  </div>
                  <CityAutocomplete
                    cityId={`edit-search-city-${search.id}`}
                    countryId={`edit-search-country-${search.id}`}
                    city={editedSearch.city}
                    country={editedSearch.country}
                    onChange={({ city, country }) =>
                      setEditedSearch({ ...editedSearch, city, country })
                    }
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Button type="submit" size="sm" disabled={busySearchId === search.id}>
                    {t('account.save')}
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={handleCancelEdit}>
                    {t('account.cancel')}
                  </Button>
                </div>
              </form>
            ) : (
              <div
                key={search.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-foreground">{search.keywords}</span>
                    {search.is_active && <Badge variant="primary">{t('account.activeBadge')}</Badge>}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {search.city}, {search.country}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    disabled={busySearchId === search.id}
                    onClick={() => handleToggleActive(search)}
                  >
                    {search.is_active ? t('account.deactivate') : t('account.activate')}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={busySearchId === search.id}
                    onClick={() => handleStartEdit(search)}
                  >
                    {t('account.edit')}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={busySearchId === search.id}
                    onClick={() => handleDeleteSearch(search)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    {t('account.delete')}
                  </Button>
                </div>
              </div>
            ),
          )}

          <form onSubmit={handleCreateSearch} className="flex flex-col gap-3 border-t border-border pt-4">
            <h3 className="text-sm font-semibold text-foreground">{t('account.newSearch')}</h3>
            <div className="flex flex-wrap gap-3">
              <div className="flex min-w-32 flex-1 flex-col gap-1.5">
                <Label htmlFor="new-search-keywords">{t('onboarding.searchKeywords')}</Label>
                <Input
                  id="new-search-keywords"
                  value={newSearch.keywords}
                  onChange={(e) => setNewSearch({ ...newSearch, keywords: e.target.value })}
                  required
                />
              </div>
              <CityAutocomplete
                cityId="new-search-city"
                countryId="new-search-country"
                city={newSearch.city}
                country={newSearch.country}
                onChange={({ city, country }) => setNewSearch({ ...newSearch, city, country })}
              />
            </div>
            <Button type="submit" className="w-fit">
              {t('account.addSearch')}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('account.settingsTitle')}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="account-lang">{t('account.interfaceLanguage')}</Label>
            <Select
              value={lang}
              onValueChange={(next) => {
                setLang(next)
                handleSettingChange({ interface_language: next })
              }}
            >
              <SelectTrigger id="account-lang" className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SUPPORTED_LANGUAGES.map((code) => (
                  <SelectItem key={code} value={code}>
                    {code.toUpperCase()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <fieldset className="flex flex-col gap-2.5">
            <legend className="mb-1 text-sm font-medium text-foreground">
              {t('onboarding.cvLanguageLabel')}
            </legend>
            <RadioGroup
              value={cvLanguageMode}
              onValueChange={(value) => {
                setCvLanguageMode(value)
                handleSettingChange({ cv_language_mode: value })
              }}
            >
              <label className="flex items-center gap-2.5 text-sm">
                <RadioGroupItem value="job_language" />
                {t('onboarding.cvLanguageJob')}
              </label>
              <label className="flex items-center gap-2.5 text-sm">
                <RadioGroupItem value="english" />
                {t('onboarding.cvLanguageEnglish')}
              </label>
            </RadioGroup>
          </fieldset>

          <label className="flex items-center gap-2.5 text-sm">
            <Checkbox
              checked={cvIncludePhoto}
              onCheckedChange={(checked) => {
                setCvIncludePhoto(checked === true)
                handleSettingChange({ cv_include_photo: checked === true })
              }}
            />
            {t('onboarding.cvIncludePhotoLabel')}
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('account.notificationsTitle')}</CardTitle>
          <CardDescription>{t('account.notificationsHint')}</CardDescription>
        </CardHeader>
        <CardContent>
          {!isPushSupported() ? (
            <p className="text-sm text-muted-foreground">{t('account.notificationsUnsupported')}</p>
          ) : isIOS() && !isStandalone() ? (
            <p className="text-sm text-muted-foreground">{t('account.notificationsIosHint')}</p>
          ) : notificationStatus === 'granted' ? (
            <p className="text-sm text-foreground">{t('account.notificationsEnabled')}</p>
          ) : notificationStatus === 'denied' ? (
            <p className="text-sm text-destructive">{t('account.notificationsDenied')}</p>
          ) : notificationStatus === 'error' ? (
            <p className="text-sm text-destructive">{t('account.notificationsError')}</p>
          ) : (
            <Button type="button" disabled={notificationStatus === 'requesting'} onClick={handleEnableNotifications}>
              {t('account.notificationsEnable')}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
