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

/** Der Mittelpunkt mehrerer Marken — worauf die Karte zeigt, wenn sie sich öffnet. */
export function mitte(marken: Ortsmarke[]): Ortsmarke {
    if (!marken.length) return {breite: 52.52, laenge: 13.405}
    const summe = marken.reduce((bisher, marke) => ({
        breite: bisher.breite + marke.breite, laenge: bisher.laenge + marke.laenge,
    }), {breite: 0, laenge: 0})
    return {breite: summe.breite / marken.length, laenge: summe.laenge / marken.length}
}
