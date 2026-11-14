import { cn } from '@/lib/utils'

function Textarea({ className, ...props }) {
  return (
    <textarea
      className={cn(
        'flex min-h-24 w-full rounded-field border border-input bg-card px-3.5 py-3 text-base leading-[1.45] text-foreground placeholder:text-muted-foreground outline-none transition-[border-color,box-shadow]',
        'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20',
        'aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
