import AppUpdateBanner from './AppUpdateBanner'
import { useAppUpdateAvailable } from '../lib/appUpdate'
import ProfileCompletionBanner from './ProfileCompletionBanner'

// Avvisi di sistema in cima alla pagina, uno alla volta (DESIGN.md §5,
// mockup `jobs-avvisi`): prima la nuova versione, poi il profilo incompleto.
export default function SystemBanner() {
  const updateAvailable = useAppUpdateAvailable()
  return updateAvailable ? <AppUpdateBanner /> : <ProfileCompletionBanner />
}
