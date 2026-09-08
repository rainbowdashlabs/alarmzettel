/**
 * Polar-Koordinaten as the dispatch system prints them: where the Einsatzadresse lies seen from
 * the station, as a bearing from grid north and a straight-line distance.
 *
 * The coordinates are ETRS89 / UTM 33N, so plane trigonometry is exact enough — across Berlin the
 * projection distorts by well under the metre the sheet rounds to. Checked against a real slip:
 * Junker-Jörg-Straße 36 to Archenholdstraße 21 gives 336,6°/2,842 km against the printed
 * 336,6°/2,849 km.
 */
export interface Punkt {
    ostwert: number
    nordwert: number
}

/** Under a kilometre the leading zero is a space, which is how the original prints it. */
function entfernung(meter: number): string {
    const geschrieben = (meter / 1000).toFixed(3).replace('.', ',')
    return geschrieben.startsWith('0,') ? ` ${geschrieben.slice(1)}` : geschrieben
}

/** Luftlinie in Kilometern. Grundlage der geschätzten Fahrzeiten im Ablaufplan. */
export function entfernungKm(von: Punkt, nach: Punkt): number {
    return Math.hypot(nach.ostwert - von.ostwert, nach.nordwert - von.nordwert) / 1000
}

export function polarKoordinaten(von: Punkt, nach: Punkt): string {
    const ost = nach.ostwert - von.ostwert
    const nord = nach.nordwert - von.nordwert
    const grad = (Math.atan2(ost, nord) * 180 / Math.PI + 360) % 360
    return `${grad.toFixed(1).replace('.', ',')}°/${entfernung(Math.hypot(ost, nord))} km`
}
