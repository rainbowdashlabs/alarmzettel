/**
 * Turns a crew strength into the Trupp line the sheet prints.
 *
 * The Trupps fill in a fixed order and each takes a fixed number of people: Staffelführer and
 * machinist together, then Angriffs-, Wasser- and Schlauchtrupp with two each, and the Melder
 * alone. A strength that does not fill a Trupp completely still names it, so 3 reads as SF, AT
 * the same way 4 does. Mirrors `backend/src/data/staerke.py`.
 */
const TRUPPS: [string, number][] = [['SF', 2], ['AT', 2], ['WT', 2], ['ST', 2], ['ME', 1]]

export function truppText(staerke: number): string {
    if (!Number.isFinite(staerke) || staerke <= 0) return ''
    const namen: string[] = []
    let besetzt = 0
    for (const [name, koepfe] of TRUPPS) {
        namen.push(name)
        besetzt += koepfe
        if (besetzt >= staerke) break
    }
    return `Stärke=${staerke}: ${namen.join(', ')}`
}

export function staerkeAusText(text: string): number | null {
    const treffer = /St(?:ä|ae)rke\s*=?\s*(\d+)/i.exec(text ?? '')
    return treffer?.[1] ? Number(treffer[1]) : null
}
