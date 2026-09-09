/**
 * Von den amtlichen Koordinaten zu denen, die eine Karte versteht.
 *
 * Der Adressdienst liefert ETRS89 / UTM 33N — darauf rechnen die Polar-Koordinaten des
 * Alarmzettels, weil Berlin darin eben liegt. Kartenkacheln stehen dagegen in WGS 84, also muss
 * die Projektion für die Karte einmal rückwärts gerechnet werden.
 *
 * Die Reihenentwicklung ist die übliche für die transversale Mercator-Projektion; auf der Fläche
 * einer Stadt liegt sie im Millimeterbereich. Geprüft wird sie gegen Punkte, die derselbe
 * Berliner Dienst in beiden Systemen ausgibt.
 */
import type {Punkt} from './polar'

/** GRS 80, die Bezugsfläche von ETRS89. */
const A = 6378137.0
const F = 1 / 298.257222101
const K0 = 0.9996
const OSTVERSATZ = 500000
/** Zone 33 reicht von 12° bis 18° Ost, ihr Mittelmeridian liegt bei 15°. */
const MITTELMERIDIAN = 15

export interface Ortsmarke {
    breite: number
    laenge: number
}

export function utm33ZuWgs84(punkt: Punkt): Ortsmarke {
    const e2 = F * (2 - F)
    const e1 = (1 - Math.sqrt(1 - e2)) / (1 + Math.sqrt(1 - e2))
    const x = punkt.ostwert - OSTVERSATZ
    const bogen = punkt.nordwert / K0

    const mu = bogen / (A * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    const breiteFuss = mu
        + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu)
        + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu)
        + (151 * e1 ** 3 / 96) * Math.sin(6 * mu)
        + (1097 * e1 ** 4 / 512) * Math.sin(8 * mu)

    const sin = Math.sin(breiteFuss)
    const cos = Math.cos(breiteFuss)
    const tan = Math.tan(breiteFuss)
    const eStrich2 = e2 / (1 - e2)
    const c1 = eStrich2 * cos ** 2
    const t1 = tan ** 2
    const n1 = A / Math.sqrt(1 - e2 * sin ** 2)
    const r1 = A * (1 - e2) / (1 - e2 * sin ** 2) ** 1.5
    const d = x / (n1 * K0)

    const breite = breiteFuss - (n1 * tan / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * eStrich2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * eStrich2 - 3 * c1 ** 2) * d ** 6 / 720)
    const laenge = (
        d
        - (1 + 2 * t1 + c1) * d ** 3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * eStrich2 + 24 * t1 ** 2) * d ** 5 / 120
    ) / cos

    return {
        breite: breite * 180 / Math.PI,
        laenge: MITTELMERIDIAN + laenge * 180 / Math.PI,
    }
}

/**
 * Und dieselbe Projektion vorwärts: von der Marke, die jemand auf der Karte gesetzt hat, zu den
 * Koordinaten, auf denen Entfernung und Polar-Koordinaten rechnen.
 */
export function wgs84ZuUtm33(marke: Ortsmarke): Punkt {
    const e2 = F * (2 - F)
    const eStrich2 = e2 / (1 - e2)
    const breite = marke.breite * Math.PI / 180
    const laenge = (marke.laenge - MITTELMERIDIAN) * Math.PI / 180

    const sin = Math.sin(breite)
    const cos = Math.cos(breite)
    const tan = Math.tan(breite)
    const n = A / Math.sqrt(1 - e2 * sin ** 2)
    const t = tan ** 2
    const c = eStrich2 * cos ** 2
    const a1 = laenge * cos

    const m = A * (
        (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * breite
        - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * Math.sin(2 * breite)
        + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * Math.sin(4 * breite)
        - (35 * e2 ** 3 / 3072) * Math.sin(6 * breite))

    const ostwert = K0 * n * (
        a1
        + (1 - t + c) * a1 ** 3 / 6
        + (5 - 18 * t + t ** 2 + 72 * c - 58 * eStrich2) * a1 ** 5 / 120
    ) + OSTVERSATZ
    const nordwert = K0 * (m + n * tan * (
        a1 ** 2 / 2
        + (5 - t + 9 * c + 4 * c ** 2) * a1 ** 4 / 24
        + (61 - 58 * t + t ** 2 + 600 * c - 330 * eStrich2) * a1 ** 6 / 720))

    return {ostwert, nordwert}
}

/**
 * Ein Koordinatenpaar, wie es aus einer Karte kommt: „52.486300, 13.521500“. Leer oder unlesbar
 * heißt, dass die Adresse selbst nachgeschlagen wird.
 */
export function markeAusText(text: string): Ortsmarke | null {
    const teile = text.split(',').map(stueck => Number(stueck.trim()))
    if (teile.length !== 2 || teile.some(wert => !Number.isFinite(wert))) return null
    const [breite, laenge] = teile as [number, number]
    if (Math.abs(breite) > 90 || Math.abs(laenge) > 180) return null
    return {breite, laenge}
}

/** Wie ein Paar geschrieben wird: sechs Nachkommastellen sind gut zehn Zentimeter. */
export function markeAlsText(marke: Ortsmarke): string {
    return `${marke.breite.toFixed(6)}, ${marke.laenge.toFixed(6)}`
}

/** Der Mittelpunkt mehrerer Marken — worauf die Karte zeigt, wenn sie sich öffnet. */
export function mitte(marken: Ortsmarke[]): Ortsmarke {
    if (!marken.length) return {breite: 52.52, laenge: 13.405}
    const summe = marken.reduce((bisher, marke) => ({
        breite: bisher.breite + marke.breite, laenge: bisher.laenge + marke.laenge,
    }), {breite: 0, laenge: 0})
    return {breite: summe.breite / marken.length, laenge: summe.laenge / marken.length}
}
