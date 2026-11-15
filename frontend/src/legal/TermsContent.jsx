// Termini di servizio mostrati agli utenti (Sprint 67).
// Testo di riferimento versionato: Docs/legal/termini-servizio-it.md e Docs/legal/terms-of-service-en.md.
// Qualunque modifica sostanziale va riportata anche lì e accompagnata da un nuovo numero di versione nel backend.
import { Link } from 'react-router-dom'
import { formatLegalDate, normalizeLang } from './format'
import { BulletList, ControllerEmail, ControllerName, LegalArticle, LegalTitle, Section } from './shared'

function TermsIt({ info, version, date, minAge }) {
  const lang = 'it'
  return (
    <LegalArticle>
      <LegalTitle>Termini di servizio</LegalTitle>
      <p>
        <strong>
          Versione {version} — in vigore dal {date}
        </strong>
      </p>
      <p>
        Questi termini regolano l'uso di App-apply ("l'app"), fornita da <ControllerName info={info} lang={lang} /> (
        <ControllerEmail info={info} lang={lang} />
        ). Registrandoti e usando l'app li accetti.
      </p>

      <Section defaultOpen title="1. Il servizio">
        <p>
          L'app raccoglie offerte di lavoro da fonti pubbliche in base alle ricerche che salvi, ne valuta l'affinità con
          il tuo profilo e ti aiuta a preparare CV, lettere di presentazione e messaggi, anche con l'aiuto
          dell'intelligenza artificiale. L'app è oggi in <strong>fase di test</strong> riservata a utenti invitati:
          funzioni, limiti e disponibilità possono cambiare.
        </p>
      </Section>

      <Section title="2. Account">
        <BulletList>
          <li>
            Per registrarti servono un codice d'invito valido, un indirizzo email che controlli e almeno{' '}
            <strong>{minAge} anni</strong> di età.
          </li>
          <li>
            Sei responsabile della riservatezza della tua password e di quanto avviene con il tuo account. Avvisaci
            subito se sospetti un accesso non autorizzato.
          </li>
          <li>
            Un account è personale: non puoi cederlo né usarlo per conto di altri senza il nostro consenso.
          </li>
        </BulletList>
      </Section>

      <Section title="3. Uso consentito">
        <p>Ti impegni a:</p>
        <BulletList>
          <li>
            inserire nel profilo informazioni <strong>vere</strong> e riferite a te;
          </li>
          <li>
            usare i documenti generati sotto la tua responsabilità, verificandone il contenuto prima di inviarli: l'app
            produce proposte, eventuali informazioni inesatte o non veritiere inviate a terzi sono una tua
            responsabilità;
          </li>
          <li>
            inserire dati di altre persone (es. il destinatario di un messaggio) solo se hai un motivo legittimo per
            contattarle;
          </li>
          <li>
            non usare l'app per attività illecite, per molestie o spam, e non tentare di aggirarne i limiti, di accedere
            a dati altrui, di sovraccaricarla o di automatizzarne l'uso.
          </li>
        </BulletList>
      </Section>

      <Section title="4. Offerte di lavoro e fonti terze">
        <p>
          Le offerte provengono da fonti terze (es. annunci pubblici su LinkedIn). Non siamo affiliati a tali fonti né ai
          datori di lavoro, non garantiamo che le offerte siano complete, aggiornate o ancora disponibili, e la
          candidatura avviene sempre sul sito dell'inserzionista. Punteggi e valutazioni sono indicazioni automatiche,
          non una garanzia di risultato.
        </p>
      </Section>

      <Section title="5. Intelligenza artificiale">
        <p>
          I contenuti generati dall'AI possono contenere errori. Non garantiamo alcun esito delle tue candidature.
          Dettagli sul trattamento dei dati nell'
          <Link to="/privacy" className="text-primary underline">
            Informativa privacy
          </Link>
          .
        </p>
      </Section>

      <Section title="6. Piani, massimali e credito">
        <p>
          Ogni piano prevede massimali giornalieri per le singole azioni; l'app ti avvisa quando ne raggiungi uno. Oltre
          i massimali alcune azioni possono essere eseguite a credito, scalando dal saldo il prezzo previsto; i messaggi
          della chat degli editor scalano sempre il credito. Nella fase di test il credito è assegnato dal titolare e
          non è previsto alcun pagamento online; il credito non è convertibile in denaro.
        </p>
      </Section>

      <Section title="7. Disponibilità e modifiche del servizio">
        <p>
          Il servizio è fornito "così com'è", nella fase di test e senza garanzia di continuità: può essere interrotto
          per manutenzione, guasti di fornitori terzi (es. fonte delle offerte, servizi AI) o modificato. Ti consigliamo
          di scaricare i documenti che ti servono.
        </p>
      </Section>

      <Section title="8. Sospensione e cancellazione">
        <p>
          Puoi cancellare il tuo account in ogni momento da Impostazioni: tutti i tuoi dati vengono eliminati. Possiamo
          sospendere o chiudere un account che violi questi termini o metta a rischio il servizio o altri utenti,
          informandoti salvo urgenza.
        </p>
      </Section>

      <Section title="9. Responsabilità">
        <p>
          Nei limiti consentiti dalla legge, non rispondiamo di danni indiretti derivanti dall'uso dell'app,
          dall'indisponibilità del servizio o dal contenuto delle offerte di terzi. Restano salvi i diritti inderogabili
          riconosciuti al consumatore.
        </p>
      </Section>

      <Section title="10. Modifiche ai termini">
        <p>
          Possiamo aggiornare questi termini. Le modifiche sostanziali ti saranno segnalate nell'app e, per continuare a
          usarla, ti sarà chiesto di accettarle.
        </p>
      </Section>

      <Section title="11. Legge applicabile">
        <p>
          Si applica la legge italiana. Se sei un consumatore, è competente il foro del luogo in cui risiedi o sei
          domiciliato.
        </p>
      </Section>
    </LegalArticle>
  )
}

function TermsEn({ info, version, date, minAge }) {
  const lang = 'en'
  return (
    <LegalArticle>
      <LegalTitle>Terms of service</LegalTitle>
      <p>
        <strong>
          Version {version} — effective from {date}
        </strong>
      </p>
      <p>
        These terms govern the use of App-apply ("the app"), provided by <ControllerName info={info} lang={lang} /> (
        <ControllerEmail info={info} lang={lang} />
        ). By registering for and using the app you accept them.
      </p>

      <Section defaultOpen title="1. The service">
        <p>
          The app collects job offers from public sources based on the searches you save, assesses how well they match
          your profile and helps you prepare CVs, cover letters and messages, including with the help of artificial
          intelligence. The app is currently in a <strong>test phase</strong> reserved for invited users: features,
          limits and availability may change.
        </p>
      </Section>

      <Section title="2. Account">
        <BulletList>
          <li>
            To register you need a valid invitation code, an email address you control and to be at least{' '}
            <strong>{minAge} years</strong> old.
          </li>
          <li>
            You are responsible for keeping your password confidential and for everything that happens with your
            account. Let us know immediately if you suspect unauthorised access.
          </li>
          <li>
            An account is personal: you may not transfer it or use it on behalf of others without our consent.
          </li>
        </BulletList>
      </Section>

      <Section title="3. Permitted use">
        <p>You agree to:</p>
        <BulletList>
          <li>
            enter <strong>truthful</strong> information about yourself in your profile;
          </li>
          <li>
            use the generated documents under your own responsibility, checking their content before sending them: the
            app produces suggestions, and any inaccurate or untruthful information sent to third parties is your
            responsibility;
          </li>
          <li>
            enter other people's data (e.g. the recipient of a message) only if you have a legitimate reason to contact
            them;
          </li>
          <li>
            not use the app for unlawful activities, harassment or spam, and not attempt to circumvent its limits,
            access other people's data, overload it or automate its use.
          </li>
        </BulletList>
      </Section>

      <Section title="4. Job offers and third-party sources">
        <p>
          Job offers come from third-party sources (e.g. public job postings on LinkedIn). We are not affiliated with
          those sources or with employers, we do not guarantee that job offers are complete, up to date or still
          available, and applications are always made on the advertiser's website. Scores and assessments are automated
          indications, not a guarantee of results.
        </p>
      </Section>

      <Section title="5. Artificial intelligence">
        <p>
          AI-generated content may contain errors. We do not guarantee any outcome of your applications. Details on data
          processing are in the{' '}
          <Link to="/privacy" className="text-primary underline">
            Privacy policy
          </Link>
          .
        </p>
      </Section>

      <Section title="6. Plans, limits and credit">
        <p>
          Each plan sets daily limits for individual actions; the app warns you when you reach one. Beyond the limits,
          some actions can be performed using credit, deducting the applicable price from your balance; messages in the
          editors' chat always use credit. During the test phase credit is assigned by the controller and no online
          payment is provided; credit cannot be converted into money.
        </p>
      </Section>

      <Section title="7. Availability and changes to the service">
        <p>
          The service is provided "as is", in the test phase and with no guarantee of continuity: it may be interrupted
          for maintenance or due to failures of third-party providers (e.g. the source of job offers, AI services), or
          modified. We recommend that you download the documents you need.
        </p>
      </Section>

      <Section title="8. Suspension and deletion">
        <p>
          You can delete your account at any time from Settings: all your data is erased. We may suspend or close an
          account that breaches these terms or puts the service or other users at risk, informing you except in urgent
          cases.
        </p>
      </Section>

      <Section title="9. Liability">
        <p>
          To the extent permitted by law, we are not liable for indirect damages arising from the use of the app, the
          unavailability of the service or the content of third-party job offers. The mandatory rights granted to
          consumers remain unaffected.
        </p>
      </Section>

      <Section title="10. Changes to the terms">
        <p>
          We may update these terms. Substantial changes will be notified to you in the app and, to continue using it,
          you will be asked to accept them.
        </p>
      </Section>

      <Section title="11. Governing law">
        <p>
          Italian law applies. If you are a consumer, the courts of the place where you reside or are domiciled have
          jurisdiction.
        </p>
      </Section>
    </LegalArticle>
  )
}

export default function TermsContent({ lang, info }) {
  if (!info) return null
  const language = normalizeLang(lang)
  const props = {
    info,
    version: info.terms?.version ?? '',
    date: formatLegalDate(info.terms?.date, language),
    minAge: info.min_age ?? 16,
  }
  return language === 'it' ? <TermsIt {...props} /> : <TermsEn {...props} />
}
