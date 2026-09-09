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
    /** Dieser Browser folgt der Sitzung mit einem Lesetoken: sehen ja, schreiben nein. */
    nurLesen: boolean
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

/**
 * Das Token, mit dem eine Sitzung nur angesehen werden kann. Es entsteht beim ersten Fragen und
 * bleibt danach dasselbe. Den Link daraus baut der Browser selbst — er weiß, unter welcher
 * Adresse er erreichbar ist, der Server hinter einem Proxy nicht unbedingt.
 */
export async function lesetoken(token: string): Promise<string> {
    const {data} = await client.post<{token: string, url: string}>(
        `/api/sitzung/${token}/lesetoken`)
    return data.token
}

/** Macht diese Sitzung zur laufenden — das ist Wechseln und Beitreten in einem. */
export async function sitzungUebernehmen(token: string): Promise<Sitzungskopf> {
    const {data} = await client.post<Sitzungskopf>(`/api/sitzung/${token}/uebernehmen`)
    return data
}
