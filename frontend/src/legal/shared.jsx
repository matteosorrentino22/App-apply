import { ChevronDown } from 'lucide-react'

// Piccoli componenti di presentazione condivisi da PrivacyContent e TermsContent (Sprint 67).
// Sprint 79 (mockup `legal-privacy`, `legal-terms`): ogni sezione è una
// fisarmonica nativa (<details>), il testo è lo stesso. `defaultOpen` sulla
// prima sezione.

const MISSING_LABEL = { it: '[da completare]', en: '[to be completed]' }

export function LegalArticle({ children }) {
  return <article className="flex flex-col gap-3 text-[15px] leading-relaxed text-foreground">{children}</article>
}

export function LegalTitle({ children }) {
  return <h1 className="text-[28px] font-bold leading-tight tracking-[-0.01em]">{children}</h1>
}

export function Section({ title, defaultOpen = false, children }) {
  return (
    <details open={defaultOpen} className="group rounded-card border border-border bg-card shadow-card">
      <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 rounded-card px-4 py-3 outline-none focus-visible:ring-3 focus-visible:ring-ring/30 [&::-webkit-details-marker]:hidden">
        <h2 className="text-base font-bold leading-snug text-foreground">{title}</h2>
        <ChevronDown className="h-5 w-5 shrink-0 text-chip-foreground transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="flex flex-col gap-2 px-4 pb-4">{children}</div>
    </details>
  )
}

export function BulletList({ children }) {
  return <ul className="list-disc pl-5 flex flex-col gap-1">{children}</ul>
}

export function LegalTable({ head, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="bg-muted">
            {head.map((cell, i) => (
              <th key={i} className="border border-border p-2 font-semibold">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className="border border-border p-2 align-top">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ExternalLink({ href, children }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline">
      {children}
    </a>
  )
}

export function Placeholder({ lang }) {
  return <span className="rounded bg-amber-100 px-1 text-amber-900">{MISSING_LABEL[lang] ?? MISSING_LABEL.en}</span>
}

export function ControllerName({ info, lang }) {
  const name = info?.controller?.name?.trim()
  return name ? <>{name}</> : <Placeholder lang={lang} />
}

export function ControllerAddress({ info }) {
  const address = info?.controller?.address?.trim()
  return address ? <>{', ' + address}</> : null
}

export function ControllerEmail({ info, lang }) {
  const email = info?.controller?.email?.trim()
  if (!email) return <Placeholder lang={lang} />
  return (
    <a href={'mailto:' + email} className="text-primary underline">
      {email}
    </a>
  )
}
