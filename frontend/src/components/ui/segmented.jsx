import { cn } from '@/lib/utils'

// Controllo a segmenti (DESIGN.md §6): 2–3 opzioni esclusive, con radio
// nativi nascosti per la tastiera (frecce) e gli screen reader.
function SegmentedControl({ name, value, onChange, options, label, disabled = false, className }) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn('grid auto-cols-fr grid-flow-col gap-1 rounded-field bg-secondary p-1', disabled && 'opacity-45', className)}
    >
      {options.map((option) => {
        const checked = option.value === value
        return (
          <label
            key={option.value}
            className={cn(
              'flex min-h-10 cursor-pointer items-center justify-center rounded-[10px] px-2 text-center text-sm leading-tight transition-colors has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/30',
              checked ? 'bg-card font-bold text-foreground shadow-card' : 'font-semibold text-muted-foreground',
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={checked}
              disabled={disabled}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            {option.label}
          </label>
        )
      })}
    </div>
  )
}

export { SegmentedControl }
