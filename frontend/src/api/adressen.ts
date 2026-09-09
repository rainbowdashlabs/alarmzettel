import client from './http'
import {markeAusText, wgs84ZuUtm33} from '../scripts/geo'
import type {Adresse} from '../interfaces/Alarm'

/**
 * One thing the address field can offer. Until a house number has been typed these are streets
 * and carry no coordinates; after one they are single doors and do.
 */
export interface Adressvorschlag {
    beschriftung: string
    strasse: string
    hnr: string
    plz: string
    ort: string
    ostwert: number | null
    nordwert: number | null
}

/** One door, with the official coordinates in ETRS89 / UTM 33N. */
export interface Adresspunkt {
    strasse: string
    hnr: string
    plz: string
    ort: string
    ostwert: number
    nordwert: number
}

let bereit: Promise<boolean> | null = null

/**
 * Whether the server has an address list to answer from. Asked once: the list is downloaded in
 * the background after a fresh install, and completion stays out of the way until it is there.
 */
export function adressdienstBereit(): Promise<boolean> {
    if (!bereit) {
        bereit = client.get('/api/adressen/status')
            .then(antwort => Boolean(antwort.data?.verfuegbar))
            .catch(() => false)
    }
    return bereit
}

export async function suchen(text: string): Promise<Adressvorschlag[]> {
    if (text.trim().length < 2 || !await adressdienstBereit()) return []
    try {
        const antwort = await client.get('/api/adressen/suche', {params: {q: text}})
        return antwort.data ?? []
    } catch {
        return []
    }
}

const gefunden = new Map<string, Adresspunkt | null>()

/**
 * One address, looked up once and remembered. The station is asked for on every keystroke that
 * changes an Einsatzadresse, and it is the same station every time.
 */
export async function adresspunkt(strasse: string, hnr: string, plz = ''): Promise<Adresspunkt | null> {
    if (!strasse.trim() || !hnr.trim()) return null
    const schluessel = `${strasse}|${hnr}|${plz}`.trim().toLowerCase()
    const bekannt = gefunden.get(schluessel)
    if (bekannt !== undefined) return bekannt
    if (!await adressdienstBereit()) return null
    try {
        const antwort = await client.get('/api/adressen', {params: {strasse, hnr, plz}})
        const punkt: Adresspunkt | null = antwort.data ?? null
        gefunden.set(schluessel, punkt)
        return punkt
    } catch {
        return null
    }
}

/**
 * Der Punkt zu einer Adresse. Steht an ihr ein eigener, gilt der und es wird nichts
 * nachgeschlagen: jemand hat ihn auf der Karte gesetzt, weil die Straße ihn nicht trifft.
 */
export function zuPunkt(adresse: Adresse): Promise<Adresspunkt | null> {
    const marke = markeAusText(adresse.koordinaten ?? '')
    if (marke) {
        const punkt = wgs84ZuUtm33(marke)
        return Promise.resolve({...punkt, plz: adresse.plz, ort: adresse.ort} as Adresspunkt)
    }
    return adresspunkt(adresse.strasse, adresse.hnr, adresse.plz)
}
