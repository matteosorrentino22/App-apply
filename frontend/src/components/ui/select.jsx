import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const Select = SelectPrimitive.Root
const SelectValue = SelectPrimitive.Value

function SelectTrigger({ className, children, ...props }) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        'flex h-12 w-full items-center justify-between gap-2 rounded-field border border-input bg-card px-3.5 text-left text-base text-foreground outline-none transition-[border-color,box-shadow]',
        'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20',
        'data-[state=open]:border-ring data-[state=open]:ring-3 data-[state=open]:ring-ring/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

function SelectContent({ className, children, position = 'popper', ...props }) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position={position}
        className={cn(
          'z-50 max-h-[var(--radix-select-content-available-height)] min-w-[8rem] overflow-y-auto rounded-field border border-border bg-card p-1.5 text-foreground shadow-popover',
          position === 'popper' &&
            'data-[side=bottom]:translate-y-1.5 w-[var(--radix-select-trigger-width)]',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

function SelectItem({ className, children, ...props }) {
  return (
    <SelectPrimitive.Item
      className={cn(
        'relative flex min-h-11 cursor-pointer items-center justify-between gap-2 rounded-[8px] px-3 py-2 text-[15px] outline-none select-none',
        'focus:bg-tint data-[state=checked]:font-semibold data-[state=checked]:text-primary',
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <SelectPrimitive.ItemIndicator>
        <Check className="h-3.5 w-3.5 text-primary" />
      </SelectPrimitive.ItemIndicator>
    </SelectPrimitive.Item>
  )
}

export { Select, SelectValue, SelectTrigger, SelectContent, SelectItem }
