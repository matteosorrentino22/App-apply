export const EMPTY_CONSENTS = { privacy: false, terms: false, age: false }

export function allConsentsGiven(consents) {
  return consents.privacy && consents.terms && consents.age
}
