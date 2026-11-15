import { ChevronDown, ChevronUp, Plus, Sparkles, Trash2 } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import RichBulletInput from '@/components/RichBulletInput'
import { AccordionSection } from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { CV_LIMITS, plainText } from '../../utils/draftLimits'

// Sezioni dell'editor del CV (Sprint 76, mockup `cv-editor`): stesse
// sezioni e stesse operazioni di prima, ciascuna in una fisarmonica.
// I campi ricchi restano `RichBulletInput` (condiviso con il Profilo,
// nessun cambio di props né di comportamento). I pulsanti "Aggiungi" si
// disattivano al limite del server (utils/draftLimits.js), con il motivo.

const iconButton =
  'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-field text-chip-foreground outline-none hover:bg-tint focus-visible:ring-3 focus-visible:ring-ring/30 disabled:pointer-events-none disabled:opacity-30'

export function IconButton({ label, className, children, ...props }) {
  return (
    <button type="button" aria-label={label} title={label} className={cn(iconButton, className)} {...props}>
      {children}
    </button>
  )
}

export function MoveButtons({ index, length, onMove }) {
  const { t } = useLanguage()
  return (
    <>
      <IconButton label={t('cvEditor.moveUp')} disabled={index === 0} onClick={() => onMove(index, -1)}>
        <ChevronUp className="h-5 w-5" aria-hidden="true" />
      </IconButton>
      <IconButton label={t('cvEditor.moveDown')} disabled={index === length - 1} onClick={() => onMove(index, 1)}>
        <ChevronDown className="h-5 w-5" aria-hidden="true" />
      </IconButton>
    </>
  )
}

export function RemoveButton({ label, onClick }) {
  return (
    <IconButton label={label} onClick={onClick} className="text-destructive-text">
      <Trash2 className="h-5 w-5" aria-hidden="true" />
    </IconButton>
  )
}

// "Aggiungi …" a tutta larghezza; al limite disattivato con il motivo sotto.
export function AddButton({ label, onClick, atLimit, limitText }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Button variant="secondary" className="w-full" onClick={onClick} disabled={atLimit}>
        <Plus className="h-5 w-5" aria-hidden="true" />
        {label}
      </Button>
      {atLimit ? <p className="text-center text-xs text-muted-foreground">{limitText}</p> : null}
    </div>
  )
}

function countLabel(t, count, oneKey, manyKey) {
  return count === 1 ? t(oneKey) : t(manyKey).replace('{count}', count)
}

export function SummarySection({ value, onChange }) {
  const { t } = useLanguage()
  return (
    <AccordionSection title={t('cvEditor.summaryLabel')} defaultOpen data-testid="cv-section-summary">
      <RichBulletInput value={value} onChange={onChange} />
    </AccordionSection>
  )
}

export function QualificationSection({ value, onChange }) {
  const { t } = useLanguage()
  return (
    <AccordionSection title={t('cvEditor.qualificationLabel')} summary={plainText(value)}>
      <RichBulletInput value={value} onChange={onChange} />
    </AccordionSection>
  )
}

export function AreasSection({ areas, onUpdate, onRemove, onAdd, onMove }) {
  const { t } = useLanguage()
  return (
    <AccordionSection
      title={t('cvEditor.areasLabel')}
      summary={countLabel(t, areas.length, 'cvEditor.areasCountOne', 'cvEditor.areasCountMany')}
    >
      {areas.map((area, index) => (
        <div key={index} className="flex flex-col gap-1.5 rounded-field bg-secondary p-2.5">
          <RichBulletInput value={area} onChange={(text) => onUpdate(index, text)} />
          <div className="flex items-center justify-end">
            <MoveButtons index={index} length={areas.length} onMove={onMove} />
            <RemoveButton label={t('cvEditor.removeArea')} onClick={() => onRemove(index)} />
          </div>
        </div>
      ))}
      <AddButton
        label={t('cvEditor.addArea')}
        onClick={() => onAdd()}
        atLimit={areas.length >= CV_LIMITS.areas}
        limitText={t('cvEditor.limitAreas').replace('{max}', CV_LIMITS.areas)}
      />
    </AccordionSection>
  )
}

function BulletRow({ bullet, index, length, focused, onChange, onToggleShown, onToggleFocus, onMove, onRemove }) {
  const { t } = useLanguage()
  return (
    <div className="flex flex-col gap-1.5 rounded-field bg-secondary p-2.5">
      <RichBulletInput value={bullet.text} onChange={onChange} />
      <div className="flex flex-wrap items-center justify-between gap-1">
        <label className="flex min-h-10 cursor-pointer items-center gap-2.5 px-1 text-[15px] text-foreground">
          <Checkbox checked={bullet.shown} onCheckedChange={(checked) => onToggleShown(checked === true)} />
          {t('cvEditor.bulletShown')}
        </label>
        <div className="flex items-center">
          <IconButton
            label={t('cvEditor.chatFocusToggle')}
            aria-pressed={focused}
            onClick={onToggleFocus}
            className={focused ? 'bg-primary text-primary-foreground hover:bg-primary/90' : ''}
          >
            <Sparkles className="h-5 w-5" aria-hidden="true" />
          </IconButton>
          <MoveButtons index={index} length={length} onMove={onMove} />
          <RemoveButton label={t('cvEditor.removeBullet')} onClick={onRemove} />
        </div>
      </div>
    </div>
  )
}

function ExperienceItem({ exp, expIndex, isFocused, handlers }) {
  const { t } = useLanguage()
  const meta = [exp.location, exp.dates].filter(Boolean).join(' | ')
  return (
    <AccordionSection nested headingLevel={3} title={exp.company} summary={plainText(exp.role)} data-testid="cv-experience">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="break-words text-base font-bold text-foreground">{exp.company}</p>
          {meta ? <p className="text-sm text-muted-foreground">{meta}</p> : null}
        </div>
        <label className="flex shrink-0 items-center gap-2.5 text-sm text-muted-foreground">
          {t('cvEditor.showInCv')}
          <Switch checked={exp.shown} onCheckedChange={(checked) => handlers.updateExperience(expIndex, { shown: checked })} />
        </label>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>{t('cvEditor.roleLabel')}</Label>
        <RichBulletInput value={exp.role} onChange={(text) => handlers.updateExperience(expIndex, { role: text })} />
      </div>
      <div className="flex flex-col gap-2">
        <Label>{t('cvEditor.bulletsLabel')}</Label>
        {exp.bullets.map((bullet, bulletIndex) => (
          <BulletRow
            key={bullet.id || bulletIndex}
            bullet={bullet}
            index={bulletIndex}
            length={exp.bullets.length}
            focused={isFocused(bullet.id)}
            onChange={(text) => handlers.updateBullet(expIndex, bulletIndex, { text })}
            onToggleShown={(shown) => handlers.updateBullet(expIndex, bulletIndex, { shown })}
            onToggleFocus={() => handlers.toggleFocusBullet(exp.profile_experience_id, bullet.id)}
            onMove={(index, delta) => handlers.moveBullet(expIndex, index, delta)}
            onRemove={() => handlers.removeBullet(expIndex, bulletIndex)}
          />
        ))}
        <AddButton
          label={t('cvEditor.addBullet')}
          onClick={() => handlers.addBullet(expIndex)}
          atLimit={exp.bullets.length >= CV_LIMITS.bulletsPerExperience}
          limitText={t('cvEditor.limitBullets').replace('{max}', CV_LIMITS.bulletsPerExperience)}
        />
      </div>
    </AccordionSection>
  )
}

export function ExperiencesSection({ experiences, isFocused, handlers }) {
  const { t } = useLanguage()
  return (
    <AccordionSection
      title={t('cvEditor.experiencesLabel')}
      summary={countLabel(t, experiences.length, 'cvEditor.companiesCountOne', 'cvEditor.companiesCountMany')}
    >
      {experiences.map((exp, expIndex) => (
        <ExperienceItem key={exp.profile_experience_id ?? expIndex} exp={exp} expIndex={expIndex} isFocused={isFocused} handlers={handlers} />
      ))}
    </AccordionSection>
  )
}

export function EducationsSection({ educations, onUpdate, onRemove, onAdd }) {
  const { t } = useLanguage()
  const text = (index, field, max) => ({
    value: educations[index][field],
    maxLength: max,
    onChange: (event) => onUpdate(index, { [field]: event.target.value }),
  })
  return (
    <AccordionSection
      title={t('cvEditor.educationsLabel')}
      summary={countLabel(t, educations.length, 'cvEditor.entriesCountOne', 'cvEditor.entriesCountMany')}
    >
      {educations.map((edu, index) => (
        <div key={index} className="flex flex-col gap-3 rounded-field border border-border p-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('cvEditor.institutionLabel')}>
              <Input {...text(index, 'institution', CV_LIMITS.educationText)} />
            </Field>
            <Field label={t('cvEditor.educationTitleLabel')}>
              <Input {...text(index, 'title', CV_LIMITS.educationText)} />
            </Field>
            <Field label={t('cvEditor.educationLocationLabel')}>
              <Input {...text(index, 'location', CV_LIMITS.educationText)} />
            </Field>
            <Field label={t('cvEditor.educationDatesLabel')}>
              <Input {...text(index, 'dates', CV_LIMITS.educationDates)} />
            </Field>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>{t('cvEditor.educationNotesLabel')}</Label>
            <RichBulletInput value={edu.notes} onChange={(notes) => onUpdate(index, { notes })} />
          </div>
          <Button variant="text" className="w-fit text-destructive-text" onClick={() => onRemove(index)}>
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {t('cvEditor.removeEducation')}
          </Button>
        </div>
      ))}
      <AddButton
        label={t('cvEditor.addEducation')}
        onClick={onAdd}
        atLimit={educations.length >= CV_LIMITS.educations}
        limitText={t('cvEditor.limitEducations').replace('{max}', CV_LIMITS.educations)}
      />
    </AccordionSection>
  )
}

// Competenze / certificazioni: voci del profilo, spuntate se nel CV.
export function ChecklistSection({ title, items, selected, onToggle }) {
  const { t } = useLanguage()
  return (
    <AccordionSection
      title={title}
      summary={items.length ? t('cvEditor.selectedCount').replace('{count}', selected.length).replace('{total}', items.length) : ''}
    >
      {items.length === 0 ? <p className="text-sm text-muted-foreground">{t('cvEditor.noProfileItems')}</p> : null}
      <div className="flex flex-col gap-1">
        {items.map((item) => (
          <label key={item.id} className="flex min-h-11 cursor-pointer items-center gap-3 text-[15px] text-foreground">
            <Checkbox checked={selected.includes(item.name)} onCheckedChange={() => onToggle(item.name)} />
            <span className="min-w-0 break-words">{item.name}</span>
          </label>
        ))}
      </div>
    </AccordionSection>
  )
}

export function LanguagesSection({ languages, nameOptions, levelOptions, onUpdate, onRemove, onAdd }) {
  const { t } = useLanguage()
  return (
    <AccordionSection title={t('cvEditor.languagesLabel')} summary={languages.length ? String(languages.length) : ''}>
      {languages.map((item, index) => (
        <div key={index} className="flex items-end gap-2">
          <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-1.5">
              <Label>{t('cvEditor.languageLabel')}</Label>
              <Select value={item.language} onValueChange={(value) => onUpdate(index, { language: value })}>
                <SelectTrigger aria-label={t('cvEditor.languageLabel')}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {nameOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex min-w-0 flex-col gap-1.5">
              <Label>{t('cvEditor.levelLabel')}</Label>
              <Select value={item.level} onValueChange={(value) => onUpdate(index, { level: value })}>
                <SelectTrigger aria-label={t('cvEditor.levelLabel')}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {levelOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <RemoveButton label={t('cvEditor.removeLanguage')} onClick={() => onRemove(index)} />
        </div>
      ))}
      <AddButton
        label={t('cvEditor.addLanguage')}
        onClick={onAdd}
        atLimit={languages.length >= CV_LIMITS.languages}
        limitText={t('cvEditor.limitLanguages').replace('{max}', CV_LIMITS.languages)}
      />
    </AccordionSection>
  )
}
