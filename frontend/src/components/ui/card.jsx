import { cn } from '@/lib/utils'

function Card({ className, ...props }) {
  return (
    <div
      className={cn(
        'rounded-card border border-border bg-card text-card-foreground shadow-card',
        className,
      )}
      {...props}
    />
  )
}

// Sprint 80: tolti CardHeader/Title/Description/Content/Footer, non più usati.
export { Card }
