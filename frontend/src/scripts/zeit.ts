/**
 * Zeitpunkte im Ablaufplan sind ISO-Zeichenketten ohne Zone — `2026-09-19T08:15` — genau das,
 * was ein `datetime-local`-Feld liefert.
 *
 * Gerechnet wird auf den Zahlen selbst und nicht über `Date`, weil ein Übungstag in einer Zone
 * stattfindet und eine Umrechnung nach UTC und zurück nur Sommerzeitfehler einbringt.
 */
const MUSTER = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/

function zerlegen(zeitpunkt: string): { tag: string, minuten: number } | null {
    const treffer = MUSTER.exec(zeitpunkt)
    if (!treffer) return null
    return {tag: `${treffer[1]}-${treffer[2]}-${treffer[3]}`,
            minuten: Number(treffer[4]) * 60 + Number(treffer[5])}
}

/** Minuten seit dem Beginn der Zeitrechnung des Plans, damit sich zwei Zeitpunkte vergleichen lassen. */
export function alsMinuten(zeitpunkt: string): number | null {
    const teile = zerlegen(zeitpunkt)
    if (!teile) return null
    return Math.floor(Date.UTC(
        Number(teile.tag.slice(0, 4)), Number(teile.tag.slice(5, 7)) - 1,
        Number(teile.tag.slice(8, 10))) / 60000) + teile.minuten
}

export function dauer(von: string, bis: string): number | null {
    const anfang = alsMinuten(von)
    const ende = alsMinuten(bis)
    return anfang === null || ende === null ? null : ende - anfang
}

export function verschieben(zeitpunkt: string, minuten: number): string {
    const teile = zerlegen(zeitpunkt)
    if (!teile) return zeitpunkt
    const tag = new Date(`${teile.tag}T00:00:00Z`)
    tag.setUTCMinutes(tag.getUTCMinutes() + teile.minuten + minuten)
    return tag.toISOString().slice(0, 16)
}

export function uhrzeit(zeitpunkt: string): string {
    const teile = zerlegen(zeitpunkt)
    if (!teile) return ''
    return `${String(Math.floor(teile.minuten / 60)).padStart(2, '0')}:` +
        String(teile.minuten % 60).padStart(2, '0')
}

export function tagVon(zeitpunkt: string): string {
    return zerlegen(zeitpunkt)?.tag ?? ''
}

export function zeitpunkt(tag: string, uhr: string): string {
    return `${tag}T${uhr}`
}

/** Zwei Zeiträume überschneiden sich, wenn keiner ganz vor dem anderen liegt. */
export function ueberschneidet(vonA: string, bisA: string, vonB: string, bisB: string): boolean {
    const a1 = alsMinuten(vonA), a2 = alsMinuten(bisA)
    const b1 = alsMinuten(vonB), b2 = alsMinuten(bisB)
    if (a1 === null || a2 === null || b1 === null || b2 === null) return false
    return a1 < b2 && b1 < a2
}
