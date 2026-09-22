// score_match/score_gaps possono contenere sia il vecchio formato (stringa
// unica) sia il nuovo (oggetto {label, reason}, sprint corrente): i job già
// in lista prima del cambio di schema restano nel vecchio formato, mai
// retroattivamente convertiti.
export function scoreItemLabel(item) {
  return typeof item === 'string' ? item : item?.label || ''
}

export function scoreItemReason(item) {
  return typeof item === 'string' ? null : item?.reason || null
}
