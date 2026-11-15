import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, Info, WifiOff } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { fetchLegalInfo } from '../api/legal'
import PrivacyContent from '../legal/PrivacyContent'
import TermsContent from '../legal/TermsContent'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'

// Pagine pubbliche /privacy e /terms (Sprint 67): testo nella PWA, versioni,
// date e titolare da GET /api/legal/. Aspetto Sprint 79 (mockup
// `legal-privacy`, `legal-terms`): sezioni a fisarmonica (legal/shared.jsx),
// stesso testo.
export default function LegalPage({ document }) {
  const { t, lang } = useLanguage()
  const navigate = useNavigate()
  // Sprint 80: prima, se /api/legal/ non rispondeva, la pagina restava in
  // caricamento per sempre; ora errore con "Riprova".
  const [info, setInfo] = useState(null)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    fetchLegalInfo()
      .then((data) => active && setInfo(data))
      .catch(() => active && setFailed(true))
    return () => {
      active = false
    }
  }, [attempt])
  const Content = document === 'terms' ? TermsContent : PrivacyContent

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 pb-6 pt-3 lg:pt-6">
      <button
        type="button"
        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
        className="-ml-2 flex min-h-11 w-fit items-center gap-1 rounded-field px-2 text-base font-semibold text-primary outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/30"
      >
        <ChevronLeft className="h-5 w-5" aria-hidden="true" />
        {t('legal.back')}
      </button>
      {failed && !info ? (
        <EmptyState
          icon={WifiOff}
          title={t('legal.loadError')}
          action={
            <Button
              size="lg"
              className="w-full"
              onClick={() => {
                setFailed(false)
                setAttempt((n) => n + 1)
              }}
            >
              {t('common.retry')}
            </Button>
          }
        />
      ) : !info ? (
        <div className="flex justify-center py-10">
          <Spinner size={28} />
        </div>
      ) : (
        <>
          {!info.controller?.complete ? (
            <Banner variant="note" icon={Info} role="alert">
              {t('legal.controllerMissing')}
            </Banner>
          ) : null}
          <Content lang={lang} info={info} />
        </>
      )}
    </div>
  )
}
