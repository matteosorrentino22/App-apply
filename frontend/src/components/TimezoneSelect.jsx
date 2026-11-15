import { useMemo } from 'react'
import { browserTimeZone, timeZoneOptions } from '../utils/date'
import { cn } from '@/lib/utils'

// Select nativo (Sprint 70): circa 400 fusi IANA, più comodo da scorrere
// e cercare con la tastiera del dispositivo che un menu personalizzato.
export default function TimezoneSelect({ id, value, onChange, className, disabled }) {
  const options = useMemo(() => timeZoneOptions([value, browserTimeZone()]), [value])
  return (
    <select
      id={id}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className={cn(
        'h-12 w-full rounded-field border border-input bg-card px-3.5 text-base text-foreground outline-none',
        'focus:border-ring focus:ring-3 focus:ring-ring/20 disabled:opacity-45',
        className,
      )}
    >
      {options.map((zone) => (
        <option key={zone} value={zone}>
          {zone.replaceAll('_', ' ')}
        </option>
      ))}
    </select>
  )
}
