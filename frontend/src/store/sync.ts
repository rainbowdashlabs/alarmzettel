import {reactive, watch} from 'vue'
import client from '../api/http'
import {arbeitsmappe, ersetzen, uebernehmen} from './arbeitsmappe'
import {flach, rund, TRENNER, type Flachbild} from '../scripts/flach'
import type {Arbeitsmappe} from '../interfaces/Alarm'

interface Aenderung {
    pfad: string
    wert?: unknown
    weg?: boolean
}

interface Antwort {
    stand: number
    aenderungen: (Aenderung & { stand: number, wer: string })[]
}

export const verbindung = reactive({
    token: null as string | null,
    wer: '',
    stand: 0,
    laeuft: false,
    fehler: null as string | null,
    zuletzt: null as number | null,
})

/**
 * The last state we know the server had, path by path. Everything hangs off the difference
 * between this and what is on screen: that difference is exactly what this browser has changed
 * and not yet sent, which is also what must survive an incoming change.
 */
let serverBild: Flachbild = {}

let takt: number | undefined
let anstehend = false
let laeuftGerade = false

const TAKT_MS = 3000
const RUHE_MS = 400
const SPEICHER = 'alarmzettel_arbeitsraum'

/**
 * Which workspace this browser is in, remembered across a reload. Without it, refreshing the page
 * — or following a link out and back — quietly drops someone out of the shared room while they
 * carry on typing into a copy only they can see.
 */
function merken(token: string, wer: string) {
    try {
        localStorage.setItem(SPEICHER, JSON.stringify({token, wer}))
    } catch { /* a browser with storage blocked simply does not reconnect */ }
}

function vergessen() {
    try {
        localStorage.removeItem(SPEICHER)
    } catch { /* nothing to do */ }
}

function gemerkt(): { token: string, wer: string } | null {
    try {
        const roh = localStorage.getItem(SPEICHER)
        return roh ? JSON.parse(roh) : null
    } catch {
        return null
    }
}

function gleich(a: unknown, b: unknown): boolean {
    return a === b || JSON.stringify(a) === JSON.stringify(b)
}

/** Every path that still exists, plus every prefix of one, so a lookup is a single check. */
function vorhandeneStellen(bild: Flachbild): Set<string> {
    const stellen = new Set<string>()
    for (const pfad of Object.keys(bild)) {
        const teile = pfad.split(TRENNER)
        for (let laenge = 1; laenge <= teile.length; laenge++) {
            stellen.add(teile.slice(0, laenge).join(TRENNER))
        }
    }
    return stellen
}

/**
 * The shortest prefix of a removed path that is gone entirely — the entity itself rather than
 * one of its fields.
 *
 * Deleting an Alarm removes its fields, and marking only those as gone is not enough: the entity
 * has no tombstone of its own, so the next person to edit it — not yet knowing it was deleted —
 * writes one field back and the whole thing returns. Burying the entity stops that.
 */
function grabstelle(pfad: string, vorhanden: Set<string>): string {
    const teile = pfad.split(TRENNER)
    for (let laenge = 2; laenge < teile.length; laenge++) {
        const praefix = teile.slice(0, laenge).join(TRENNER)
        if (!vorhanden.has(praefix)) return praefix
    }
    return pfad
}

/** The difference between two flat images, as the change list the server understands. */
function unterschied(vorher: Flachbild, nachher: Flachbild): Aenderung[] {
    const aenderungen: Aenderung[] = []
    for (const [pfad, wert] of Object.entries(nachher)) {
        if (!gleich(vorher[pfad], wert)) aenderungen.push({pfad, wert})
    }

    const vorhanden = vorhandeneStellen(nachher)
    const begraben = new Set<string>()
    for (const pfad of Object.keys(vorher)) {
        if (pfad in nachher) continue
        const stelle = grabstelle(pfad, vorhanden)
        if (begraben.has(stelle)) continue
        begraben.add(stelle)
        aenderungen.push({pfad: stelle, weg: true})
    }
    return aenderungen
}

/**
 * Folds a change list into a flat image.
 *
 * A tombstone names an entity, not a field, so it has to take everything below it with it.
 * Removing only the named path would leave the entity's fields lying in the shadow, and the next
 * rebuild would put the entity back together out of them.
 */
function anlegen(bild: Flachbild, aenderungen: Aenderung[]): Flachbild {
    const ergebnis = {...bild}
    for (const aenderung of aenderungen) {
        if (!aenderung.weg) {
            ergebnis[aenderung.pfad] = aenderung.wert
            continue
        }
        delete ergebnis[aenderung.pfad]
        const unterhalb = aenderung.pfad + TRENNER
        for (const pfad of Object.keys(ergebnis)) {
            if (pfad.startsWith(unterhalb)) delete ergebnis[pfad]
        }
    }
    return ergebnis
}

/**
 * Folds an exchange into the shadow and rebuilds the screen.
 *
 * `gesendetBild` is what this browser looked like at the moment it sent. Anything typed during
 * the round trip is the difference between that and now, and it has to survive: without it, an
 * incoming change would wipe out whatever someone is in the middle of writing. Everything else
 * comes from the shadow, which is the merged truth.
 */
function einarbeiten(antwort: Antwort, gesendet: Aenderung[], gesendetBild: Flachbild) {
    const waehrenddessen = unterschied(gesendetBild, flach(arbeitsmappe))
    serverBild = anlegen(anlegen(serverBild, gesendet), antwort.aenderungen)

    verbindung.stand = antwort.stand
    verbindung.zuletzt = Date.now()
    ersetzen(uebernehmen(rund(anlegen(serverBild, waehrenddessen)) as Arbeitsmappe))
}

async function austauschen() {
    if (!verbindung.token || laeuftGerade) {
        anstehend = anstehend || laeuftGerade
        return
    }
    laeuftGerade = true
    try {
        const gesendetBild = flach(arbeitsmappe)
        const gesendet = unterschied(serverBild, gesendetBild)
        const {data} = await client.post<Antwort>(
            `/api/freigabe/${verbindung.token}/aenderungen`,
            {seit: verbindung.stand, wer: verbindung.wer, aenderungen: gesendet})
        einarbeiten(data, gesendet, gesendetBild)
        verbindung.fehler = null
    } catch (fehler) {
        // A failed exchange changes nothing: the edits stay in the difference and go with the
        // next one, so a dropped connection costs time rather than work.
        verbindung.fehler = (fehler as Error).message
    } finally {
        laeuftGerade = false
        if (anstehend) {
            anstehend = false
            void austauschen()
        }
    }
}

/**
 * Exchanges now instead of waiting for the next beat. Wanted before something is produced from
 * the working set — a PDF, a download — so it is made from what everyone has, not from what this
 * browser happened to have a moment ago.
 */
export async function jetztAbgleichen() {
    if (verbindung.token) await austauschen()
}

let ruhe: number | undefined

function beiAenderung() {
    if (!verbindung.token) return
    window.clearTimeout(ruhe)
    ruhe = window.setTimeout(austauschen, RUHE_MS)
}

watch(arbeitsmappe, beiAenderung, {deep: true})

/**
 * Joins a workspace. Everything on screen is replaced by what the workspace holds — a shared
 * room is not merged with whatever happened to be in this browser, or one person's leftovers
 * would land on everyone else.
 */
export async function beitreten(token: string, wer: string) {
    // Fetched before anything is thrown away, so a workspace that cannot be reached leaves this
    // browser with what it had.
    const {data} = await client.get<Antwort>(
        `/api/freigabe/${token}/aenderungen`, {params: {seit: 0}})

    verlassen()
    verbindung.token = token
    verbindung.wer = wer
    verbindung.stand = 0
    serverBild = {}
    ersetzen(uebernehmen({version: 1, alarme: []} as unknown as Arbeitsmappe))

    einarbeiten(data, [], flach(arbeitsmappe))
    verbindung.laeuft = true
    merken(token, wer)
    takt = window.setInterval(austauschen, TAKT_MS)
}

/**
 * Rejoins the workspace this browser was last in. Called once at startup; a workspace that has
 * expired or been deleted simply leaves the browser on its own copy.
 */
export async function wiederaufnehmen() {
    const gespeichert = gemerkt()
    if (!gespeichert) return
    try {
        await beitreten(gespeichert.token, gespeichert.wer)
    } catch {
        vergessen()
    }
}

/** The shadow, for tests that need to see what this browser thinks the server holds. */
export function schatten(): Flachbild {
    return {...serverBild}
}

export function verlassen() {
    vergessen()
    window.clearInterval(takt)
    window.clearTimeout(ruhe)
    takt = undefined
    verbindung.token = null
    verbindung.laeuft = false
    verbindung.fehler = null
    serverBild = {}
}
