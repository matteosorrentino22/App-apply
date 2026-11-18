// Controlli di impaginazione riutilizzabili (Sprint 81). Dopo lo Sprint 80
// erano sfuggiti difetti visibili solo su iPhone: campi data più larghi
// della card, campi sovrapposti, ruoli rientrati fuori dal riquadro. Il
// controllo della sola larghezza della pagina non li vedeva (la pagina non
// scorre di lato: è il contenuto a uscire dalla sua card). Qui si cercano:
//  - scroll orizzontale della pagina;
//  - elementi che escono dal rettangolo del loro contenitore visibile
//    (il primo antenato con bordo o sfondo: card, riquadro, campo);
//  - coppie di controlli che si sovrappongono.

export async function findLayoutIssues(page) {
  return page.evaluate(() => {
    const issues = []
    const vw = window.innerWidth
    const de = document.documentElement
    if (de.scrollWidth > vw + 1) issues.push(`pagina più larga dello schermo: ${de.scrollWidth} > ${vw}`)

    const describe = (el) => {
      const text = (el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
      const id = el.id ? `#${el.id}` : ''
      return `${el.tagName.toLowerCase()}${id}${text ? ` "${text}"` : ''}`
    }
    // Stili calcolati una volta per elemento: sulle pagine lunghe il
    // controllo altrimenti diventa lentissimo (soprattutto in WebKit).
    const styles = new Map()
    const style = (el) => {
      let s = styles.get(el)
      if (!s) {
        s = getComputedStyle(el)
        styles.set(el, s)
      }
      return s
    }
    const visible = (el) => {
      const s = style(el)
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false
      const r = el.getBoundingClientRect()
      if (r.width < 1 || r.height < 1) return false
      // sr-only e simili: ritagliati a 1 px
      if (s.position === 'absolute' && r.width <= 1 && r.height <= 1) return false
      return !el.closest('[hidden], [aria-hidden="true"], .sr-only')
    }
    const isBox = (el) => {
      if (el === document.body || el === de || el.tagName === 'MAIN') return false
      const s = style(el)
      const border = ['Top', 'Right', 'Bottom', 'Left'].some((side) => parseFloat(s[`border${side}Width`]) > 0 && s[`border${side}Style`] !== 'none')
      const bg = s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent'
      return border || bg
    }
    const scrollsX = (el) => ['auto', 'scroll'].includes(style(el).overflowX)
    // 1) Elementi fuori dal loro contenitore
    const candidates = document.querySelectorAll(
      'input:not([type=hidden]), select, textarea, button, a[href], label, [role=switch], [role=combobox], [role=checkbox], h1, h2, h3, p, img, li',
    )
    const seen = new Set()
    for (const el of candidates) {
      if (!visible(el) || el.closest('[data-allow-overflow]')) continue
      // Elementi posizionati (menu a tendina, badge, aree di tocco) non
      // seguono il flusso del contenitore: esclusi.
      let floats = style(el).position === 'absolute'
      let box = el.parentElement
      let scrolled = false
      while (box && !isBox(box)) {
        if (scrollsX(box)) scrolled = true
        if (style(box).position === 'absolute') floats = true
        box = box.parentElement
      }
      if (!box || floats || scrolled || scrollsX(box)) continue
      const r = el.getBoundingClientRect()
      const b = box.getBoundingClientRect()
      const out = Math.max(b.left - r.left, r.right - b.right)
      if (out > 1.5) {
        const key = `${describe(el)} esce di ${Math.round(out)} px da ${describe(box).slice(0, 30)}`
        if (!seen.has(key)) {
          seen.add(key)
          issues.push(key)
        }
      }
    }

    // 2) Controlli sovrapposti. Si confrontano solo controlli dello stesso
    // "strato": il contenuto che scorre sotto una barra fissa (barra di tab,
    // barra azione, pannello) non è un difetto.
    // Strato = barra fissa o appiccicata (sticky) e contenitore che scorre:
    // due controlli in strati diversi possono sovrapporsi scorrendo.
    const layer = (el) => {
      const parts = []
      for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
        const s = style(n)
        if (s.position === 'fixed' || s.position === 'sticky') parts.push(n)
        else if (s.overflowY === 'auto' || s.overflowY === 'scroll') parts.push(n)
      }
      return parts
    }
    const controls = [...document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea, button, [role=combobox], [role=switch], a[href]')].filter(
      (el) => visible(el) && !el.closest('[data-allow-overflow], [role=menu], [role=listbox]') && !(el.type === 'file' && el.classList.contains('sr-only')),
    )
    const rects = controls.map((el) => el.getBoundingClientRect())
    const layers = controls.map((el) => layer(el))
    const sameLayer = (i, j) => layers[i].length === layers[j].length && layers[i].every((n, k) => n === layers[j][k])
    for (let i = 0; i < controls.length; i++) {
      for (let j = i + 1; j < controls.length; j++) {
        const r1 = rects[i]
        const r2 = rects[j]
        const w = Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left)
        const h = Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top)
        if (w <= 2 || h <= 2) continue
        const a = controls[i]
        const c = controls[j]
        if (a.contains(c) || c.contains(a) || !sameLayer(i, j)) continue
        issues.push(`sovrapposti: ${describe(a)} e ${describe(c)} (${Math.round(w)}×${Math.round(h)} px)`)
      }
    }

    // 3) Contenuto coperto dalle barre fisse in basso, a fine pagina
    const bars = [...document.querySelectorAll('[data-testid="action-bar"], nav.app-tabbar')].filter(visible)
    if (bars.length) {
      const top = Math.min(...bars.map((bar) => bar.getBoundingClientRect().top))
      // Sprint 84: con lo zoom della dimensione del testo i rettangoli sono in
      // px dello schermo, gli stili calcolati in px CSS: stessa unità.
      const scale = document.body.offsetWidth ? document.body.getBoundingClientRect().width / document.body.offsetWidth : 1
      const pad = (parseFloat(style(document.querySelector('#root > div') || document.body).paddingBottom) || 0) * scale
      const barsHeight = window.innerHeight - top
      if (pad + 1 < barsHeight) issues.push(`spazio in fondo (${Math.round(pad)} px) minore delle barre fisse (${Math.round(barsHeight)} px)`)
    }
    return issues
  })
}

// Apre tutte le fisarmoniche (Profilo, editor, dettaglio) prima del
// controllo, con un clic da script: un pulsante coperto da una barra fissa
// non va "raggiunto" con lo scorrimento.
export async function openAllSections(page) {
  for (let pass = 0; pass < 3; pass++) {
    const opened = await page.evaluate(() => {
      const closed = [...document.querySelectorAll('main button[aria-expanded="false"]:not([aria-haspopup])')]
      closed.forEach((button) => button.click())
      return closed.length
    })
    if (!opened) return
    await page.waitForTimeout(200)
  }
}
