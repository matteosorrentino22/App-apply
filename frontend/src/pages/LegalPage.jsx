import { useNavigate } from 'react-router-dom'
import { ChevronLeft, Info } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import PrivacyContent from '../legal/PrivacyContent'
import TermsContent from '../legal/TermsContent'
import { Banner } from '@/components/ui/banner'
import { Spinner } from '@/components/ui/spinner'

// Pagine pubbliche /privacy e /terms (Sprint 67): testo nella PWA, versioni,
// date e titolare da GET /api/legal/. Aspetto Sprint 79 (mockup
// `legal-privacy`, `legal-terms`): sezioni a fisarmonica (legal/shared.jsx),
// stesso testo.
export default function LegalPage({ document }) {
  const { t, lang } = useLanguage()
  const navigate = useNavigate()
  const info = useLegalInfo()
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
      {!info ? (
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
