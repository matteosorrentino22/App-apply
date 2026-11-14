<!-- Versioned reference text (Sprint 67). The version shown to users is in frontend/src/legal/; placeholders are replaced with the values from GET /api/legal/ (versions and dates in the backend, controller details from environment variables). -->

# Privacy policy

**Version {{PRIVACY_VERSION}} — effective from {{PRIVACY_DATE}}**

This privacy policy is provided pursuant to Articles 13 and 14 of Regulation (EU) 2016/679 ("GDPR") to anyone who registers for and uses App-apply (hereinafter "the app"), a service that collects job offers, assesses how well they match the user's profile and helps the user prepare CVs, cover letters and messages.

## 1. Data controller
{{CONTROLLER_NAME}}{{CONTROLLER_ADDRESS}} — email: {{CONTROLLER_EMAIL}}.
You can write to this address with any request concerning your data. No Data Protection Officer (DPO) has been appointed, as this is not mandatory.

## 2. What data we process
- **Account data:** login email, password (stored only in non-reversible encrypted form), interface language, time zone, plan, credit balance, registration date, email verification status, notification preference, record of your acceptance of this privacy policy and of the terms (version and date).
- **Professional profile data**, which you enter yourself or which the app extracts from the CV you upload during onboarding: first name, last name, phone number, contact email, city and country, LinkedIn profile, photo (optional), summary, work experience, education, skills, certifications, languages, career goal. The uploaded CV file is read to fill in the profile and **is not stored**.
- **Service usage data:** saved searches, collected or imported job offers with their scores and explanations, generated documents (CVs, cover letters, messages), drafts, history of chats with the AI assistant, instructions you provide, favourites, saved filters, application status.
- **Third-party data that you enter or that appears in job offers:** name and public profile of the recruiter mentioned in the job posting; name and LinkedIn profile of the recipient of a networking message you write. We ask you to enter such data only if you have a legitimate reason to contact that person.
- **Technical data:** access tokens (stored only in non-reversible encrypted form), data of your browser's push notification subscription, IP address and request data in the server's security logs, technical processing records.

**We ask you not to enter special categories of data in your profile** (Art. 9 GDPR: health, political opinions, religious beliefs, trade union membership, etc.) or data relating to criminal convictions: they are not needed for the service. If you choose to enter them, we will process them only to generate the documents you request.

## 3. Purposes and legal bases
| Purpose | Legal basis |
|---|---|
| Creating and managing your account; providing the service (collecting and assessing job offers, generating and editing documents, chat, morning notifications about new jobs and reminders in case of inactivity) | Performance of a contract (Art. 6(1)(b)) |
| Sending service emails (address verification, password recovery, deletion confirmation) | Performance of a contract (Art. 6(1)(b)) |
| Push notifications on your device | Consent, given through the browser permission and revocable at any time from the app or from the browser settings (Art. 6(1)(a)) |
| Security of the service, prevention of abuse and fraud, rate limits, technical logs | Legitimate interest of the controller in protecting the service and users' data (Art. 6(1)(f)) |
| Compliance with legal obligations and defence of rights in legal proceedings | Legal obligation (Art. 6(1)(c)) and legitimate interest (Art. 6(1)(f)) |

We do not use your data for advertising, we do not sell it and we do not disclose it to third parties for their own purposes.

## 4. Use of artificial intelligence
The app uses artificial intelligence models (Claude, through the Amazon Bedrock service) to: extract the profile from the uploaded CV, assess how well job offers match your profile (score, strengths and gaps), generate CVs, cover letters and messages, and reply in the editors' chat.
- Generated content consists of **suggestions**: always check it before using it. You are responsible for the truthfulness of the documents you send.
- The assessment of job offers is automated processing for **your exclusive use**: it serves to rank job offers for you and **does not produce decisions with legal effects** on you within the meaning of Art. 22 GDPR. It is not disclosed to employers or third parties.
- AI processing takes place **in the European Union**: requests are sent to the AWS Frankfurt region and, through Amazon Bedrock's "EU" inference profiles, can only be processed in AWS regions located in the EU. The service provider does not use the data sent to train its models.

## 5. Recipients and processors
Data is processed by the controller and, on its behalf, by providers acting as processors (Art. 28 GDPR) or as independent controllers for the services indicated:
- **Server hosting:** Hostinger International Ltd — server located in Germany (EU).
- **AI processing:** Amazon Web Services (Amazon Bedrock), EU region (Frankfurt), with processing limited to AWS regions in the EU.
- **Sending of service emails:** Google (Gmail) — the email address and the content of the message pass through Google's servers; a copy of the sent emails remains in the controller's mailbox at Google and is deleted periodically.
- **Push notifications:** your browser's push service (e.g. Google, Mozilla, Apple, Microsoft) receives only the technical identifier of the subscription and the text of the notification, which contains no data from your profile.
- **Collection of job offers:** Apify (automated collection of job postings) and LinkedIn (public job posting pages): they receive only the keywords and locations of your searches, **not** your profile data.
- **Location search:** OpenStreetMap (Nominatim), queried by our server with only the text of the city you type.
- **Sign-in with Google** (when available): Google receives the authentication request and provides us with your email address.

## 6. Transfers outside the European Union
Profile data and documents are stored and processed in the EU. Some providers (Google for emails and notifications, other push services, Apify) may also process the data indicated above in the United States: in that case the transfer is based on the EU–US adequacy decision (EU-US Data Privacy Framework) for certified providers or on the European Commission's Standard Contractual Clauses.

## 7. How long we keep data
- **Account, profile, job offers, documents, drafts and chats:** for as long as you keep your account. If you delete it, we erase them immediately, together with the files (PDFs and photos).
- **Backup copies:** kept for 7 days and then automatically deleted; deleted data also disappears from backups within this period.
- **Server security logs (with IP addresses):** 14 days.
- **Temporary data for rate limits:** 24 hours at most.
- **Access tokens:** expire after 30 days of inactivity or on logout.
- **Technical processing records** (outcome of collections, generations and chats): for the lifetime of the account; if you delete it, they remain only in anonymous form, with no reference to you.
- **Record of acceptances** of the privacy policy and terms: for the lifetime of the account.

## 8. Your rights
You have the right to request access to your data, rectification, erasure, restriction of processing and portability, and to object to processing based on legitimate interest; you can withdraw your consent to notifications at any time, without affecting prior processing.
- From the app you can, on your own: **edit** your profile, **download** all your data in a readable format (Settings → Export my data), **delete** your account and all your data (Settings → Delete account), turn off notifications.
- For anything else, write to {{CONTROLLER_EMAIL}}: we reply within one month.
- You also have the right to lodge a complaint with the **Garante per la protezione dei dati personali** (www.garanteprivacy.it) or with the authority of the EU country where you live or work.

## 9. Minimum age
The app is reserved for people aged **16 or over**. By registering you declare that you are at least 16 years old.

## 10. Cookies and storage on your device
The app **does not use profiling cookies or analytics or advertising tools**. On your device it stores only what is needed for it to work: the access token and the chosen language (the browser's local storage) and the files of the installable app (service worker), which are also needed for notifications. No consent is required for these technical tools. The administration area, used only by the controller, uses technical session cookies.

## 11. Security
We use appropriate technical and organisational measures: encrypted connection (HTTPS), passwords and tokens stored in encrypted form, access to documents allowed only to their owner through temporary links, limits on login attempts, server security updates, backups.

## 12. Changes
If we make substantial changes to this privacy policy, we will notify you in the app and, where necessary, ask you to review it again. The version in force is always available on this page.
