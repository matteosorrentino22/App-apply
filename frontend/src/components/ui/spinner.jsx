import { useLanguage } from '@/i18n/LanguageContext'
import { cn } from '@/lib/utils'

// Indicatore di attesa (mockup `collect-running`, `generazione-in-corso`):
// anello chiaro con arco nel colore primario. `framed` lo mette nel cerchio
// 56 px su --primary-soft usato dai pannelli di attesa. `label` è letto dagli
// screen reader (default "Caricamento…").
function Spinner({ size = 20, framed = false, label, className }) {
  const { t } = useLanguage()
  const ring = (
    <svg
      width={framed ? 30 : size}
      height={framed ? 30 : size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className="animate-spin motion-reduce:animate-[spin_1.6s_linear_infinite]"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
  return (
    <span role="status" className={cn('inline-flex text-primary', className)}>
      {framed ? (
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-soft">{ring}</span>
      ) : (
        ring
      )}
      <span className="sr-only">{label || t('common.loading')}</span>
    </span>
  )
}

export { Spinner }
