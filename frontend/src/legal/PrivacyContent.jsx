// Informativa privacy mostrata agli utenti (Sprint 67).
// Testo di riferimento versionato: Docs/legal/informativa-privacy-it.md e Docs/legal/privacy-policy-en.md.
// Qualunque modifica sostanziale va riportata anche lì e accompagnata da un nuovo numero di versione nel backend.
import { formatLegalDate, normalizeLang } from './format'
import {
  BulletList,
  ControllerAddress,
  ControllerEmail,
  ControllerName,
  ExternalLink,
  LegalArticle,
  LegalTable,
  LegalTitle,
  Section,
} from './shared'

function PrivacyIt({ info, version, date, minAge }) {
  const lang = 'it'
  const email = <ControllerEmail info={info} lang={lang} />
  return (
    <LegalArticle>
      <LegalTitle>Informativa sul trattamento dei dati personali</LegalTitle>
      <p>
        <strong>
          Versione {version} — in vigore dal {date}
        </strong>
      </p>
      <p>
        Questa informativa è resa ai sensi degli artt. 13 e 14 del Regolamento (UE) 2016/679 ("GDPR") a chi si registra
        e usa App-apply (di seguito "l'app"), un servizio che raccoglie offerte di lavoro, ne valuta l'affinità con il
        profilo dell'utente e lo aiuta a preparare CV, lettere di presentazione e messaggi.
      </p>

      <Section title="1. Titolare del trattamento">
        <p>
          <ControllerName info={info} lang={lang} />
          <ControllerAddress info={info} /> — email: {email}.
          <br />
          Per qualunque richiesta relativa ai tuoi dati puoi scrivere a questo indirizzo. Non è stato nominato un
          Responsabile della protezione dei dati (DPO), non essendo obbligatorio.
        </p>
      </Section>

      <Section title="2. Quali dati trattiamo">
        <BulletList>
          <li>
            <strong>Dati dell'account:</strong> email di accesso, password (conservata solo in forma cifrata non
            reversibile), lingua dell'interfaccia, fuso orario, piano, saldo del credito, data di registrazione, stato
            di verifica dell'email, preferenza sulle notifiche, registrazione delle accettazioni di questa informativa e
            dei termini (versione e data).
          </li>
          <li>
            <strong>Dati del profilo professionale</strong>, che inserisci tu o che l'app estrae dal CV che carichi in
            onboarding: nome, cognome, telefono, email di contatto, città e paese, profilo LinkedIn, foto (facoltativa),
            sommario, esperienze lavorative, istruzione, competenze, certificazioni, lingue, obiettivo professionale. Il
            file del CV caricato viene letto per compilare il profilo e <strong>non viene conservato</strong>.
          </li>
          <li>
            <strong>Dati di utilizzo del servizio:</strong> ricerche salvate, offerte raccolte o importate con i relativi
            punteggi e motivazioni, documenti generati (CV, cover letter, messaggi), bozze, cronologia delle chat con
            l'assistente AI, istruzioni che fornisci, preferiti, filtri salvati, stato delle candidature.
          </li>
          <li>
            <strong>Dati di terzi che inserisci o che compaiono nelle offerte:</strong> nome e profilo pubblico del
            recruiter indicati nell'annuncio; nome e profilo LinkedIn del destinatario di un messaggio di networking che
            scrivi tu. Ti chiediamo di inserirli solo se hai un motivo legittimo per contattare quella persona.
          </li>
          <li>
            <strong>Dati tecnici:</strong> token di accesso (conservati solo in forma cifrata non reversibile), dati
            della sottoscrizione alle notifiche push del tuo browser, indirizzo IP e dati della richiesta nei log di
            sicurezza del server, registri tecnici delle elaborazioni.
          </li>
        </BulletList>
        <p>
          <strong>Ti chiediamo di non inserire nel profilo dati particolari</strong> (art. 9 GDPR: salute, opinioni
          politiche, convinzioni religiose, appartenenza sindacale, ecc.) né dati giudiziari: non servono al servizio.
          Se scegli di inserirli, li tratteremo solo per generare i documenti che richiedi.
        </p>
      </Section>

      <Section title="3. Finalità e basi giuridiche">
        <LegalTable
          head={['Finalità', 'Base giuridica']}
          rows={[
            [
              "Creare e gestire il tuo account; fornire il servizio (raccolta e valutazione delle offerte, generazione e modifica dei documenti, chat, notifiche mattutine sui nuovi job e promemoria in caso di inattività)",
              'Esecuzione del contratto (art. 6.1.b)',
            ],
            [
              "Invio di email di servizio (verifica dell'indirizzo, recupero password, conferma di cancellazione)",
              'Esecuzione del contratto (art. 6.1.b)',
            ],
            [
              'Notifiche push sul dispositivo',
              "Consenso, espresso tramite il permesso del browser e revocabile in ogni momento dall'app o dalle impostazioni del browser (art. 6.1.a)",
            ],
            [
              'Sicurezza del servizio, prevenzione di abusi e frodi, limiti di frequenza, log tecnici',
              'Legittimo interesse del titolare a proteggere il servizio e i dati degli utenti (art. 6.1.f)',
            ],
            [
              'Adempimenti di legge e difesa di diritti in sede giudiziaria',
              'Obbligo legale (art. 6.1.c) e legittimo interesse (art. 6.1.f)',
            ],
          ]}
        />
        <p>Non usiamo i tuoi dati per pubblicità, non li vendiamo e non li cediamo a terzi per loro finalità.</p>
      </Section>

      <Section title="4. Uso dell'intelligenza artificiale">
        <p>
          L'app usa modelli di intelligenza artificiale (Claude, tramite il servizio Amazon Bedrock) per: estrarre il
          profilo dal CV caricato, valutare l'affinità delle offerte con il tuo profilo (punteggio, punti di forza e
          lacune), generare CV, lettere di presentazione e messaggi, e rispondere nella chat degli editor.
        </p>
        <BulletList>
          <li>
            I contenuti generati sono <strong>proposte</strong>: verificali sempre prima di usarli. Sei responsabile
            della veridicità dei documenti che invii.
          </li>
          <li>
            La valutazione delle offerte è un'elaborazione automatizzata a <strong>tuo esclusivo uso</strong>: serve a
            ordinare le offerte per te e <strong>non produce decisioni che abbiano effetti giuridici</strong> su di te ai
            sensi dell'art. 22 GDPR. Non viene comunicata a datori di lavoro o a terzi.
          </li>
          <li>
            Le elaborazioni AI avvengono <strong>nell'Unione Europea</strong>: le richieste sono inviate alla regione
            AWS di Francoforte e, tramite i profili di inferenza «EU» di Amazon Bedrock, possono essere elaborate solo
            in regioni AWS situate nell'UE. Il fornitore del servizio non usa i dati inviati per addestrare i modelli.
          </li>
        </BulletList>
      </Section>

      <Section title="5. Destinatari e responsabili del trattamento">
        <p>
          I dati sono trattati dal titolare e, per suo conto, da fornitori che agiscono come responsabili del
          trattamento (art. 28 GDPR) o come titolari autonomi per i servizi indicati:
        </p>
        <BulletList>
          <li>
            <strong>Hosting del server:</strong> Hostinger International Ltd — server situato in Germania (UE).
          </li>
          <li>
            <strong>Elaborazione AI:</strong> Amazon Web Services (Amazon Bedrock), regione UE (Francoforte), con
            elaborazione limitata alle regioni AWS dell'UE.
          </li>
          <li>
            <strong>Invio delle email di servizio:</strong> Google (Gmail) — l'indirizzo email e il contenuto del
            messaggio transitano sui server di Google; una copia delle email inviate resta nella casella del
            titolare presso Google e viene cancellata periodicamente.
          </li>
          <li>
            <strong>Notifiche push:</strong> il servizio push del tuo browser (es. Google, Mozilla, Apple, Microsoft)
            riceve solo l'identificativo tecnico della sottoscrizione e il testo della notifica, che non contiene dati
            del tuo profilo.
          </li>
          <li>
            <strong>Raccolta delle offerte:</strong> Apify (raccolta automatica degli annunci) e LinkedIn (pagine
            pubbliche degli annunci): ricevono solo le parole chiave e le località delle tue ricerche,{' '}
            <strong>non</strong> i dati del tuo profilo.
          </li>
          <li>
            <strong>Ricerca delle località:</strong> OpenStreetMap (Nominatim), interrogato dal nostro server con il
            solo testo della città digitata.
          </li>
          <li>
            <strong>Accesso con Google</strong> (quando sarà disponibile): Google riceve la richiesta di autenticazione
            e ci comunica il tuo indirizzo email.
          </li>
        </BulletList>
      </Section>

      <Section title="6. Trasferimenti fuori dall'Unione Europea">
        <p>
          I dati del profilo e i documenti sono conservati ed elaborati nell'UE. Alcuni fornitori (Google per le email e
          le notifiche, altri servizi push, Apify) possono trattare i dati indicati sopra anche negli Stati Uniti: in tal
          caso il trasferimento si basa sulla decisione di adeguatezza UE–USA (EU-US Data Privacy Framework) per i
          fornitori certificati o sulle Clausole contrattuali standard della Commissione europea.
        </p>
      </Section>

      <Section title="7. Per quanto tempo conserviamo i dati">
        <BulletList>
          <li>
            <strong>Account, profilo, offerte, documenti, bozze e chat:</strong> finché mantieni l'account. Se lo
            cancelli, li eliminiamo subito, insieme ai file (PDF e foto).
          </li>
          <li>
            <strong>Copie di backup:</strong> sono conservate per 7 giorni e poi cancellate automaticamente; i dati
            cancellati scompaiono anche dai backup entro questo termine.
          </li>
          <li>
            <strong>Log di sicurezza del server (con indirizzi IP):</strong> 14 giorni.
          </li>
          <li>
            <strong>Dati temporanei per i limiti di frequenza:</strong> al massimo 24 ore.
          </li>
          <li>
            <strong>Token di accesso:</strong> scadono dopo 30 giorni di inattività o al logout.
          </li>
          <li>
            <strong>Registri tecnici delle elaborazioni</strong> (esito di raccolte, generazioni e chat): per la durata
            dell'account; se lo cancelli restano solo in forma anonima, senza alcun riferimento a te.
          </li>
          <li>
            <strong>Registrazione delle accettazioni</strong> di informativa e termini: per la durata dell'account.
          </li>
        </BulletList>
      </Section>

      <Section title="8. I tuoi diritti">
        <p>
          Hai diritto di chiedere l'accesso ai tuoi dati, la rettifica, la cancellazione, la limitazione del
          trattamento, la portabilità e di opporti ai trattamenti basati sul legittimo interesse; puoi revocare in ogni
          momento il consenso alle notifiche, senza effetti sui trattamenti precedenti.
        </p>
        <BulletList>
          <li>
            Dall'app puoi in autonomia: <strong>modificare</strong> il profilo, <strong>scaricare</strong> tutti i tuoi
            dati in formato leggibile (Impostazioni → Esporta i miei dati), <strong>cancellare</strong> l'account e tutti
            i dati (Impostazioni → Elimina account), disattivare le notifiche.
          </li>
          <li>Per tutto il resto scrivi a {email}: rispondiamo entro un mese.</li>
          <li>
            Hai anche diritto di proporre reclamo al <strong>Garante per la protezione dei dati personali</strong> (
            <ExternalLink href="https://www.garanteprivacy.it">www.garanteprivacy.it</ExternalLink>) o all'autorità del
            Paese UE in cui vivi o lavori.
          </li>
        </BulletList>
      </Section>

      <Section title="9. Età minima">
        <p>
          L'app è riservata a chi ha compiuto <strong>{minAge} anni</strong>. Registrandoti dichiari di avere almeno{' '}
          {minAge} anni.
        </p>
      </Section>

      <Section title="10. Cookie e archiviazione sul dispositivo">
        <p>
          L'app <strong>non usa cookie di profilazione né strumenti di analisi o pubblicità</strong>. Sul tuo
          dispositivo salva solo ciò che serve a farla funzionare: il token di accesso e la lingua scelta (memoria
          locale del browser) e i file dell'app installabile (service worker), necessari anche per le notifiche. Per
          questi strumenti tecnici non è richiesto il consenso. L'area di amministrazione, usata solo dal titolare, usa
          cookie tecnici di sessione.
        </p>
      </Section>

      <Section title="11. Sicurezza">
        <p>
          Usiamo misure tecniche e organizzative adeguate: connessione cifrata (HTTPS), password e token conservati in
          forma cifrata, accesso ai documenti consentito solo al proprietario tramite link temporanei, limiti ai
          tentativi di accesso, aggiornamenti di sicurezza del server, backup.
        </p>
      </Section>

      <Section title="12. Modifiche">
        <p>
          Se modifichiamo questa informativa in modo sostanziale te lo segnaleremo nell'app e, dove necessario, ti
          chiederemo di prenderne visione di nuovo. La versione in vigore è sempre disponibile in questa pagina.
        </p>
      </Section>
    </LegalArticle>
  )
}

function PrivacyEn({ info, version, date, minAge }) {
  const lang = 'en'
  const email = <ControllerEmail info={info} lang={lang} />
  return (
    <LegalArticle>
      <LegalTitle>Privacy policy</LegalTitle>
      <p>
        <strong>
          Version {version} — effective from {date}
        </strong>
      </p>
      <p>
        This privacy policy is provided pursuant to Articles 13 and 14 of Regulation (EU) 2016/679 ("GDPR") to anyone
        who registers for and uses App-apply (hereinafter "the app"), a service that collects job offers, assesses how
        well they match the user's profile and helps the user prepare CVs, cover letters and messages.
      </p>

      <Section title="1. Data controller">
        <p>
          <ControllerName info={info} lang={lang} />
          <ControllerAddress info={info} /> — email: {email}.
          <br />
          You can write to this address with any request concerning your data. No Data Protection Officer (DPO) has
          been appointed, as this is not mandatory.
        </p>
      </Section>

      <Section title="2. What data we process">
        <BulletList>
          <li>
            <strong>Account data:</strong> login email, password (stored only in non-reversible encrypted form),
            interface language, time zone, plan, credit balance, registration date, email verification status,
            notification preference, record of your acceptance of this privacy policy and of the terms (version and
            date).
          </li>
          <li>
            <strong>Professional profile data</strong>, which you enter yourself or which the app extracts from the CV
            you upload during onboarding: first name, last name, phone number, contact email, city and country, LinkedIn
            profile, photo (optional), summary, work experience, education, skills, certifications, languages, career
            goal. The uploaded CV file is read to fill in the profile and <strong>is not stored</strong>.
          </li>
          <li>
            <strong>Service usage data:</strong> saved searches, collected or imported job offers with their scores and
            explanations, generated documents (CVs, cover letters, messages), drafts, history of chats with the AI
            assistant, instructions you provide, favourites, saved filters, application status.
          </li>
          <li>
            <strong>Third-party data that you enter or that appears in job offers:</strong> name and public profile of
            the recruiter mentioned in the job posting; name and LinkedIn profile of the recipient of a networking
            message you write. We ask you to enter such data only if you have a legitimate reason to contact that
            person.
          </li>
          <li>
            <strong>Technical data:</strong> access tokens (stored only in non-reversible encrypted form), data of your
            browser's push notification subscription, IP address and request data in the server's security logs,
            technical processing records.
          </li>
        </BulletList>
        <p>
          <strong>We ask you not to enter special categories of data in your profile</strong> (Art. 9 GDPR: health,
          political opinions, religious beliefs, trade union membership, etc.) or data relating to criminal
          convictions: they are not needed for the service. If you choose to enter them, we will process them only to
          generate the documents you request.
        </p>
      </Section>

      <Section title="3. Purposes and legal bases">
        <LegalTable
          head={['Purpose', 'Legal basis']}
          rows={[
            [
              'Creating and managing your account; providing the service (collecting and assessing job offers, generating and editing documents, chat, morning notifications about new jobs and reminders in case of inactivity)',
              'Performance of a contract (Art. 6(1)(b))',
            ],
            [
              'Sending service emails (address verification, password recovery, deletion confirmation)',
              'Performance of a contract (Art. 6(1)(b))',
            ],
            [
              'Push notifications on your device',
              'Consent, given through the browser permission and revocable at any time from the app or from the browser settings (Art. 6(1)(a))',
            ],
            [
              'Security of the service, prevention of abuse and fraud, rate limits, technical logs',
              "Legitimate interest of the controller in protecting the service and users' data (Art. 6(1)(f))",
            ],
            [
              'Compliance with legal obligations and defence of rights in legal proceedings',
              'Legal obligation (Art. 6(1)(c)) and legitimate interest (Art. 6(1)(f))',
            ],
          ]}
        />
        <p>
          We do not use your data for advertising, we do not sell it and we do not disclose it to third parties for
          their own purposes.
        </p>
      </Section>

      <Section title="4. Use of artificial intelligence">
        <p>
          The app uses artificial intelligence models (Claude, through the Amazon Bedrock service) to: extract the
          profile from the uploaded CV, assess how well job offers match your profile (score, strengths and gaps),
          generate CVs, cover letters and messages, and reply in the editors' chat.
        </p>
        <BulletList>
          <li>
            Generated content consists of <strong>suggestions</strong>: always check it before using it. You are
            responsible for the truthfulness of the documents you send.
          </li>
          <li>
            The assessment of job offers is automated processing for <strong>your exclusive use</strong>: it serves to
            rank job offers for you and <strong>does not produce decisions with legal effects</strong> on you within
            the meaning of Art. 22 GDPR. It is not disclosed to employers or third parties.
          </li>
          <li>
            AI processing takes place <strong>in the European Union</strong>: requests are sent to the AWS Frankfurt
            region and, through Amazon Bedrock's "EU" inference profiles, can only be processed in AWS regions located
            in the EU. The service provider does not use the data sent to train its models.
          </li>
        </BulletList>
      </Section>

      <Section title="5. Recipients and processors">
        <p>
          Data is processed by the controller and, on its behalf, by providers acting as processors (Art. 28 GDPR) or as
          independent controllers for the services indicated:
        </p>
        <BulletList>
          <li>
            <strong>Server hosting:</strong> Hostinger International Ltd — server located in Germany (EU).
          </li>
          <li>
            <strong>AI processing:</strong> Amazon Web Services (Amazon Bedrock), EU region (Frankfurt), with
            processing limited to AWS regions in the EU.
          </li>
          <li>
            <strong>Sending of service emails:</strong> Google (Gmail) — the email address and the content of the
            message pass through Google's servers; a copy of the sent emails remains in the controller's mailbox
            at Google and is deleted periodically.
          </li>
          <li>
            <strong>Push notifications:</strong> your browser's push service (e.g. Google, Mozilla, Apple, Microsoft)
            receives only the technical identifier of the subscription and the text of the notification, which contains
            no data from your profile.
          </li>
          <li>
            <strong>Collection of job offers:</strong> Apify (automated collection of job postings) and LinkedIn (public
            job posting pages): they receive only the keywords and locations of your searches, <strong>not</strong>{' '}
            your profile data.
          </li>
          <li>
            <strong>Location search:</strong> OpenStreetMap (Nominatim), queried by our server with only the text of
            the city you type.
          </li>
          <li>
            <strong>Sign-in with Google</strong> (when available): Google receives the authentication request and
            provides us with your email address.
          </li>
        </BulletList>
      </Section>

      <Section title="6. Transfers outside the European Union">
        <p>
          Profile data and documents are stored and processed in the EU. Some providers (Google for emails and
          notifications, other push services, Apify) may also process the data indicated above in the United States: in
          that case the transfer is based on the EU–US adequacy decision (EU-US Data Privacy Framework) for certified
          providers or on the European Commission's Standard Contractual Clauses.
        </p>
      </Section>

      <Section title="7. How long we keep data">
        <BulletList>
          <li>
            <strong>Account, profile, job offers, documents, drafts and chats:</strong> for as long as you keep your
            account. If you delete it, we erase them immediately, together with the files (PDFs and photos).
          </li>
          <li>
            <strong>Backup copies:</strong> kept for 7 days and then automatically deleted; deleted data also
            disappears from backups within this period.
          </li>
          <li>
            <strong>Server security logs (with IP addresses):</strong> 14 days.
          </li>
          <li>
            <strong>Temporary data for rate limits:</strong> 24 hours at most.
          </li>
          <li>
            <strong>Access tokens:</strong> expire after 30 days of inactivity or on logout.
          </li>
          <li>
            <strong>Technical processing records</strong> (outcome of collections, generations and chats): for the
            lifetime of the account; if you delete it, they remain only in anonymous form, with no reference to you.
          </li>
          <li>
            <strong>Record of acceptances</strong> of the privacy policy and terms: for the lifetime of the account.
          </li>
        </BulletList>
      </Section>

      <Section title="8. Your rights">
        <p>
          You have the right to request access to your data, rectification, erasure, restriction of processing and
          portability, and to object to processing based on legitimate interest; you can withdraw your consent to
          notifications at any time, without affecting prior processing.
        </p>
        <BulletList>
          <li>
            From the app you can, on your own: <strong>edit</strong> your profile, <strong>download</strong> all your
            data in a readable format (Settings → Export my data), <strong>delete</strong> your account and all your
            data (Settings → Delete account), turn off notifications.
          </li>
          <li>For anything else, write to {email}: we reply within one month.</li>
          <li>
            You also have the right to lodge a complaint with the{' '}
            <strong>Garante per la protezione dei dati personali</strong> (
            <ExternalLink href="https://www.garanteprivacy.it">www.garanteprivacy.it</ExternalLink>) or with the
            authority of the EU country where you live or work.
          </li>
        </BulletList>
      </Section>

      <Section title="9. Minimum age">
        <p>
          The app is reserved for people aged <strong>{minAge} or over</strong>. By registering you declare that you are
          at least {minAge} years old.
        </p>
      </Section>

      <Section title="10. Cookies and storage on your device">
        <p>
          The app <strong>does not use profiling cookies or analytics or advertising tools</strong>. On your device it
          stores only what is needed for it to work: the access token and the chosen language (the browser's local
          storage) and the files of the installable app (service worker), which are also needed for notifications. No
          consent is required for these technical tools. The administration area, used only by the controller, uses
          technical session cookies.
        </p>
      </Section>

      <Section title="11. Security">
        <p>
          We use appropriate technical and organisational measures: encrypted connection (HTTPS), passwords and tokens
          stored in encrypted form, access to documents allowed only to their owner through temporary links, limits on
          login attempts, server security updates, backups.
        </p>
      </Section>

      <Section title="12. Changes">
        <p>
          If we make substantial changes to this privacy policy, we will notify you in the app and, where necessary, ask
          you to review it again. The version in force is always available on this page.
        </p>
      </Section>
    </LegalArticle>
  )
}

export default function PrivacyContent({ lang, info }) {
  if (!info) return null
  const language = normalizeLang(lang)
  const props = {
    info,
    version: info.privacy?.version ?? '',
    date: formatLegalDate(info.privacy?.date, language),
    minAge: info.min_age ?? 16,
  }
  return language === 'it' ? <PrivacyIt {...props} /> : <PrivacyEn {...props} />
}
