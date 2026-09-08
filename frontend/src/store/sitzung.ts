/**
 * Die laufende Sitzung dieses Browsers und die, die er sonst noch kennt.
 *
 * Das Token der laufenden steht im Cookie, das der Server setzt — deshalb steht hier keines. Die
 * Liste der bekannten gehört dem Browser und nicht der Arbeitsmappe, also liegt sie im
 * `localStorage`; eine Sitzung, die der Server nicht mehr kennt, fliegt beim Öffnen heraus.
 */
import {reactive} from 'vue'
import {laufendeSitzung, sitzungAnlegen, sitzungUebernehmen, type Sitzungskopf} from '../api/sitzung'
import {arbeitsmappe, ersetzen, uebernehmen} from './arbeitsmappe'
import {beitreten, verbindung, verlassen} from './sync'
import type {Arbeitsmappe} from '../interfaces/Alarm'

const BEKANNT = 'alarmzettel_sitzungen'
const NAME = 'alarmzettel_name'

export interface BekannteSitzung {
    token: string
    beschriftung: string
    zuletzt: string
}

export const sitzung = reactive({
    token: null as string | null,
    laeuftAb: null as string | null,
    bekannt: [] as BekannteSitzung[],
})

function lesen<T>(schluessel: string, standard: T): T {
    try {
        const roh = localStorage.getItem(schluessel)
        return roh ? JSON.parse(roh) as T : standard
    } catch {
        return standard
    }
}

function schreiben(schluessel: string, wert: unknown) {
    try {
        localStorage.setItem(schluessel, JSON.stringify(wert))
    } catch { /* ein Browser, der nichts speichern will, vergisst die Liste eben */ }
}

/** Woran man eine Sitzung wiedererkennt: erstes Stichwort und wie viele Alarme darin stehen. */
function beschriftung(mappe: Arbeitsmappe): string {
    const erste = mappe.alarme[0]?.stichwort?.trim()
    const anzahl = mappe.alarme.length
    if (!anzahl) return 'leer'
    return erste ? `${erste} (${anzahl})` : `${anzahl} Alarme`
}

function merken(token: string) {
    const ohne = sitzung.bekannt.filter(eintrag => eintrag.token !== token)
    sitzung.bekannt = [{token, beschriftung: beschriftung(arbeitsmappe),
                        zuletzt: new Date().toISOString()}, ...ohne].slice(0, 20)
    schreiben(BEKANNT, sitzung.bekannt)
}

export function sitzungVergessen(token: string) {
    sitzung.bekannt = sitzung.bekannt.filter(eintrag => eintrag.token !== token)
    schreiben(BEKANNT, sitzung.bekannt)
}

export function name(): string {
    return lesen<string>(NAME, '') || 'Ich'
}

export function nameSetzen(wert: string) {
    schreiben(NAME, wert.trim())
    verbindung.wer = wert.trim() || 'Ich'
}

function uebernehmenIn(kopf: Sitzungskopf) {
    sitzung.token = kopf.token
    sitzung.laeuftAb = kopf.laeuftAb
    merken(kopf.token)
}

/**
 * Beim Start: die Sitzung aus dem Cookie aufnehmen. Gibt es keine, wird eine angelegt — mit dem,
 * was noch im `localStorage` liegt, damit die Umstellung niemandem seine Arbeit nimmt.
 */
export async function sitzungStarten() {
    sitzung.bekannt = lesen<BekannteSitzung[]>(BEKANNT, [])
    const laufend = await laufendeSitzung()
    if (laufend) {
        await beitreten(laufend.token, name())
        uebernehmenIn(laufend)
        return
    }
    const kopf = await sitzungAnlegen(arbeitsmappe)
    await beitreten(kopf.token, name())
    uebernehmenIn(kopf)
}

/** Eine leere Sitzung. Die alte bleibt liegen, sie ist ja nicht gelöscht. */
export async function neueSitzung() {
    const leer = uebernehmen({version: 1, alarme: []} as unknown as Arbeitsmappe)
    const kopf = await sitzungAnlegen(leer)
    verlassen()
    ersetzen(leer)
    await beitreten(kopf.token, name())
    uebernehmenIn(kopf)
}

/** In eine bekannte oder geteilte Sitzung wechseln. */
export async function sitzungWechseln(token: string) {
    const kopf = await sitzungUebernehmen(token)
    await beitreten(token, name())
    uebernehmenIn(kopf)
}
