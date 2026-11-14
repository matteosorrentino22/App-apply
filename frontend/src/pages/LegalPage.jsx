import { useNavigate } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import PrivacyContent from '../legal/PrivacyContent'
import TermsContent from '../legal/TermsContent'

// Pagine pubbliche /privacy e /terms (Sprint 67): testo nella PWA, versioni,
// date e titolare da GET /api/legal/.
export default function LegalPage({ document }) {
  const { t, lang } = useLanguage()
  const navigate = useNavigate()
  const info = useLegalInfo()
  const Content = document === 'terms' ? TermsContent : PrivacyContent

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-10">
      <button
        type="button"
        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
        className="w-fit text-sm font-medium text-primary hover:underline"
      >
        {t('legal.back')}
      </button>
      {!info ? (
        <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
      ) : (
        <>
          {!info.controller?.complete && (
            <p role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              {t('legal.controllerMissing')}
            </p>
          )}
          <Content lang={lang} info={info} />
        </>
      )}
    </div>
  )
}
