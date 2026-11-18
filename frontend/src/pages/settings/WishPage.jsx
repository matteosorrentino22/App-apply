import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Lock, Star } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useLanguage } from '../../i18n/LanguageContext'
import { fetchJobWish, saveJobWish } from '../../api/searches'
import { ApiError } from '../../api/client'
import CityChipsField from '@/components/CityChipsField'
import { useToast } from '@/components/ToastProvider'
import { SettingsSubpageHeader } from '@/components/settings/SettingsList'
import { ActionBar } from '@/components/ui/action-bar'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

// Lavoro dei desideri (Sprint 84, SPEC-DELTA A19, mockup `desiderio-pro`,
// `desiderio-free`): solo Pro. Descrizione (max 1000), paese e fino a 5
// città; l'AI ne ricava 1–2 keyword per una ricerca nascosta, che non si
// mostrano mai (GET/PUT /api/job-wish/ non le restituiscono). L'interruttore
// salva subito; le modifiche del modulo con "Salva".

const MAX_WISH_DESCRIPTION = 1000
const MAX_WISH_CITIES = 5

function errorText(err, t) {
  if (!(err instanceof ApiError)) return t('common.genericError')
  if (typeof err.data?.detail === 'string') return err.data.detail
  const first = Object.values(err.data || {}).flat()[0]
  return typeof first === 'string' ? first : t('common.genericError')
}

function WishLabel() {
  const { t } = useLanguage()
  return (
    <Badge variant="wish" className="gap-1 align-middle">
      <Star className="h-3 w-3 fill-current" aria-hidden="true" />
      {t('jobs.wishBadge')}
    </Badge>
  )
}

export default function WishPage() {
  const { t } = useLanguage()
  const { user } = useAuth()
  const isPro = user?.plan === 'pro'
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 pb-6 pt-3 lg:pt-6">
      <SettingsSubpageHeader title={t('wish.title')} />
      {isPro ? <WishForm /> : <WishLocked />}
    </div>
  )
}

function WishLocked() {
  const { t } = useLanguage()
  return (
    <>
      <section className="flex flex-col gap-3.5 rounded-card border border-border bg-card p-4 shadow-card" data-testid="wish-locked">
        <div className="flex items-center gap-2">
          <Badge className="gap-1 bg-primary text-primary-foreground">
            <Lock className="h-3 w-3" aria-hidden="true" />
            PRO
          </Badge>
          <span className="text-[15px] font-bold text-foreground">{t('wish.proIncluded')}</span>
        </div>
        <p className="text-[15px] leading-normal text-foreground">{t('wish.freePitch')}</p>
        <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <WishLabel />
          {t('wish.freeLabelHint')}
        </p>
      </section>
      <ActionBar stacked>
        <Link to="/settings/limits" className={cn(buttonVariants({ size: 'lg' }), 'w-full')}>
          {t('wish.discoverPro')}
        </Link>
      </ActionBar>
    </>
  )
}

function WishForm() {
  const { t } = useLanguage()
  const { refreshUser } = useAuth()
  const { showToast } = useToast()
  const [saved, setSaved] = useState(null)
  const [draft, setDraft] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchJobWish()
      .then((data) => {
        const initial = data.exists ? data : { ...data, is_active: true, description: '', country: '', cities: [] }
        setSaved(data)
        setDraft(initial)
      })
      .catch(() => showToast(t('common.genericError')))
  }, [showToast, t])

  if (!draft) {
    return (
      <div className="flex justify-center py-10">
        <Spinner size={28} />
      </div>
    )
  }

  async function save(next, successText) {
    setSaving(true)
    try {
      const data = await saveJobWish(next)
      setSaved(data)
      setDraft(data)
      refreshUser()
      showToast(successText)
      return true
    } catch (err) {
      showToast(errorText(err, t))
      return false
    } finally {
      setSaving(false)
    }
  }

  async function toggle(checked) {
    if (!saved?.exists) {
      setDraft({ ...draft, is_active: checked })
      return
    }
    // Interruttore: salva lo stato attuale (descrizione invariata, nessuna chiamata AI).
    await save({ ...saved, is_active: checked }, checked ? t('wish.activatedToast') : t('wish.deactivatedToast'))
  }

  const description = draft.description || ''
  const complete = description.trim() && draft.country && draft.cities.length > 0
  const dirty =
    !saved?.exists ||
    description !== saved.description ||
    draft.country !== saved.country ||
    draft.cities.join('|') !== (saved.cities || []).join('|')
  const descriptionChanged = !saved?.exists || description.trim() !== (saved.description || '').trim()
  const noChangesLeft = descriptionChanged && draft.changes_left_today === 0

  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <Label htmlFor="wish-active" className="text-[15px] font-semibold text-foreground">
          {t('wish.active')}
        </Label>
        <Switch id="wish-active" checked={draft.is_active} disabled={saving} label={t('wish.active')} onCheckedChange={toggle} />
      </div>

      <section className="flex flex-col gap-4 rounded-card border border-border bg-card p-4 shadow-card">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-3">
            <Label htmlFor="wish-description">{t('wish.descriptionLabel')}</Label>
            <span className="text-[13px] tabular-nums text-muted-foreground" aria-hidden="true">
              {description.length} / {MAX_WISH_DESCRIPTION}
            </span>
          </div>
          <Textarea
            id="wish-description"
            value={description}
            maxLength={MAX_WISH_DESCRIPTION}
            rows={5}
            placeholder={t('wish.descriptionPlaceholder')}
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
            className="min-h-32"
          />
          <p className="text-[13px] leading-snug text-muted-foreground" data-testid="wish-changes-left">
            {t('wish.changesLeft').replace('{count}', draft.changes_left_today)}
          </p>
        </div>
        <CityChipsField
          idPrefix="wish"
          country={draft.country}
          onCountryChange={(country) => setDraft({ ...draft, country, cities: country === draft.country ? draft.cities : [] })}
          cities={draft.cities}
          onCitiesChange={(cities) => setDraft({ ...draft, cities })}
          maxCities={MAX_WISH_CITIES}
        />
        <p className="text-sm leading-normal text-muted-foreground">
          {t('wish.explainBefore')} <WishLabel /> {t('wish.explainAfter')}
        </p>
      </section>

      <ActionBar stacked>
        <Button
          size="lg"
          className="w-full"
          disabled={saving || !complete || !dirty || noChangesLeft}
          onClick={() => save({ ...draft, description: description.trim() }, t('wish.savedToast'))}
        >
          {saving ? <Spinner size={18} /> : null}
          {t('settings.save')}
        </Button>
      </ActionBar>
    </>
  )
}
