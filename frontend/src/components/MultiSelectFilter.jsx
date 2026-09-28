import { useEffect, useRef, useState } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'

export default function MultiSelectFilter({ label, options, selected, onToggle, disabled }) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!open) return
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  return (
    <div ref={containerRef} className="relative flex items-center gap-1.5">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        className={cn(
          'rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
          selected.length > 0
            ? 'bg-primary text-primary-foreground'
            : 'bg-secondary text-muted-foreground hover:text-foreground',
        )}
      >
        {label}
        {selected.length > 0 && ` (${selected.length})`}
      </button>

      {open && (
        <div className="absolute top-full left-0 z-20 mt-1 grid min-w-40 grid-cols-2 gap-1.5 rounded-md border border-border bg-card p-2 shadow-md">
          {options.map((option) => (
            <label
              key={option.value}
              className="flex items-center gap-2 rounded px-1 py-0.5 text-sm hover:bg-secondary"
            >
              <Checkbox
                checked={selected.includes(option.value)}
                onCheckedChange={() => onToggle(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
