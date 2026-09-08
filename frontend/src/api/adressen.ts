import client from './http'
import type {Adresse} from '../interfaces/Alarm'

/** A street, and the postcode and Ortsteil one stretch of it lies in. */
export interface Strassentreffer {
    strasse: string
    plz: string
    ort: string
    anzahl: number
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

export async function strassen(suche: string): Promise<Strassentreffer[]> {
    if (suche.trim().length < 2 || !await adressdienstBereit()) return []
    try {
        const antwort = await client.get('/api/adressen/strassen', {params: {q: suche}})
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

export function zuPunkt(adresse: Adresse): Promise<Adresspunkt | null> {
    return adresspunkt(adresse.strasse, adresse.hnr, adresse.plz)
}
