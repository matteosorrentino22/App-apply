import logoMark from '@/assets/brand/logo-mark.svg'
import logoMarkLight from '@/assets/brand/logo-mark-light.svg'
import { cn } from '@/lib/utils'

// Marchio "Incontro" + wordmark (DESIGN.md §3.4, Docs/design/logo/): barra
// desktop e schermate di accesso. File SVG serviti dal nostro dominio (CSP
// img-src 'self'); con il tema scuro del sistema si usa la variante chiara.
// Il wordmark usa lo stack di font di sistema (nessun font esterno).
export default function BrandLogo({ size = 32, className }) {
  return (
    <span className={cn('flex items-center gap-2', className)}>
      <picture className="shrink-0">
        <source srcSet={logoMarkLight} media="(prefers-color-scheme: dark)" />
        <img src={logoMark} width={size} height={size} alt="" aria-hidden="true" />
      </picture>
      <span className="text-xl font-extrabold tracking-[-0.02em] text-primary">App-apply</span>
    </span>
  )
}
