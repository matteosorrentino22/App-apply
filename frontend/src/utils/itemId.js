// Id stabili di bullet e paragrafi delle bozze (Sprint 69), stessa forma di
// quelli assegnati dal server (apps/cv/draft_ids.py): 12 caratteri esadecimali.
export function newItemId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 12)
  }
  return Array.from({ length: 12 }, () => Math.floor(Math.random() * 16).toString(16)).join('')
}
