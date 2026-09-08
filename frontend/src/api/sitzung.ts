import client from './http'
import type {Arbeitsmappe} from '../interfaces/Alarm'

/**
 * Die Sitzung ist die Arbeitsmappe auf dem Server. Das Token steht in einem Cookie, das der
 * Server setzt — deshalb steht es in keinem Aufruf hier drin — und im Link, den man weitergibt.
 * Beides ist derselbe Schlüssel; eine Anmeldung gibt es nicht.
 */
export interface Sitzungskopf {
    token: string
    url: string
    laeuftAb: string
    tage: number
}

export interface GeleseneSitzung extends Sitzungskopf {
    arbeitsmappe: Arbeitsmappe
}

/** Die laufende Sitzung dieses Browsers, oder nichts, solange er keine hat. */
export async function laufendeSitzung(): Promise<GeleseneSitzung | null> {
    try {
        const {data} = await client.get<GeleseneSitzung>('/api/sitzung')
        return data
    } catch {
        return null
    }
}

export async function sitzungAnlegen(arbeitsmappe: Arbeitsmappe): Promise<Sitzungskopf> {
    const {data} = await client.post<Sitzungskopf>('/api/sitzung', arbeitsmappe)
    return data
}

export async function sitzungLesen(token: string): Promise<GeleseneSitzung> {
    const {data} = await client.get<GeleseneSitzung>(`/api/sitzung/${token}`)
    return data
}

/** Macht diese Sitzung zur laufenden — das ist Wechseln und Beitreten in einem. */
export async function sitzungUebernehmen(token: string): Promise<Sitzungskopf> {
    const {data} = await client.post<Sitzungskopf>(`/api/sitzung/${token}/uebernehmen`)
    return data
}
