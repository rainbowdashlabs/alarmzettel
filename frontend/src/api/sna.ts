import type {SnaBaum, SnaTreffer} from '../interfaces/Sna'

let geladen: Promise<SnaBaum> | null = null

/** Reference data, not user data — fetched once on first use and kept for the tab's lifetime. */
export function ladeBaum(): Promise<SnaBaum> {
    if (!geladen) {
        geladen = fetch('/sna-tree.json')
            .then(antwort => {
                if (!antwort.ok) throw new Error(`HTTP ${antwort.status}`)
                return antwort.json() as Promise<SnaBaum>
            })
            .catch(fehler => {
                geladen = null
                throw fehler
            })
    }
    return geladen
}

let index: SnaTreffer[] | null = null

/**
 * Every endpoint with one path that reaches it. The graph converges, so an endpoint can be
 * reached more than one way; the first path found is the one offered, which is enough to fill
 * the Hinweise and lets search jump straight to a code.
 */
export function endpunkte(baum: SnaBaum): SnaTreffer[] {
    if (index) return index
    const treffer: SnaTreffer[] = []
    const gesehen = new Set<string>()

    for (const disziplin of baum.disziplinen) {
        const warteschlange: { id: string, pfad: SnaTreffer['pfad'] }[] = [{id: disziplin.einstieg, pfad: []}]
        while (warteschlange.length) {
            const {id, pfad} = warteschlange.shift()!
            const knoten = baum.knoten[id]
            if (!knoten) continue
            if (knoten.code !== undefined) {
                const schluessel = `${disziplin.id}:${id}`
                if (gesehen.has(schluessel)) continue
                gesehen.add(schluessel)
                treffer.push({
                    code: knoten.code,
                    kategorie: knoten.kategorie ?? '',
                    anlass: knoten.anlass ?? '',
                    stichwort: knoten.stichwort ?? '',
                    disziplin,
                    pfad,
                })
                continue
            }
            for (const antwort of knoten.antworten ?? []) {
                warteschlange.push({
                    id: antwort.ziel,
                    pfad: [...pfad, {label: antwort.label, aussage: antwort.aussage}],
                })
            }
        }
    }
    index = treffer
    return treffer
}

export function suchen(baum: SnaBaum, text: string, grenze = 40): SnaTreffer[] {
    const begriffe = text.toLowerCase().split(/\s+/).filter(Boolean)
    if (!begriffe.length) return []
    const passend = (treffer: SnaTreffer) => {
        const heuhaufen = `${treffer.code} ${treffer.anlass} ${treffer.kategorie} ${treffer.disziplin.label}`.toLowerCase()
        return begriffe.every(begriff => heuhaufen.includes(begriff))
    }
    return endpunkte(baum).filter(passend).slice(0, grenze)
}
