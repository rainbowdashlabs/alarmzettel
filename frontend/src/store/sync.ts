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
 * Welche Sitzung dieser Browser fährt, über einen Reload hinweg. Das Token steht ohnehin im
 * Cookie; hier steht es nur mit dem Namen zusammen, unter dem gearbeitet wird.
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
 * Pfadabschnitte, unter denen Einträge mit einer eigenen id hängen. Was direkt darauf folgt, ist
 * ein Eintrag; der Abschnitt selbst ist nur die Liste, in der er steht.
 */
const LISTEN = new Set([
    'alarme', 'hinweise', 'einsatzmittel', 'fahrzeuge', 'stichwoerter', 'status', 'trupp',
    'tage', 'orte', 'personen', 'programmpunkte', 'laeufe', 'verfuegbar', 'schritte',
    'besatzung', 'rollen', 'fahrerlaubnis', 'fahrerlaubnisse',
])

/**
 * The shortest prefix of a removed path that is gone entirely — the entity itself rather than
 * one of its fields.
 *
 * Deleting an Alarm removes its fields, and marking only those as gone is not enough: the entity
 * has no tombstone of its own, so the next person to edit it — not yet knowing it was deleted —
 * writes one field back and the whole thing returns. Burying the entity stops that.
 *
 * Es muss aber ein *Eintrag* sein, nie die Liste, in der er steht. Wird der letzte Tag gelöscht,
 * ist auch `planung / tage` vollständig verschwunden — ein Grabstein darauf würde die Liste für
 * immer zumauern, denn der Server hält alles unter einem Grabstein für gelöscht. Ein Eintrag
 * erkennt sich daran, dass der Abschnitt über ihm eine Liste ist.
 */
function grabstelle(pfad: string, vorhanden: Set<string>): string {
    const teile = pfad.split(TRENNER)
    for (let laenge = 2; laenge < teile.length; laenge++) {
        const praefix = teile.slice(0, laenge).join(TRENNER)
        if (!LISTEN.has(teile[laenge - 2]!)) continue
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
 *
 * Gebaut wird nur, wenn der Server etwas mitgeschickt hat. Der Aufbau ersetzt jedes Objekt der
 * Arbeitsmappe durch ein neues, und alles, was daran hängt, hält das für eine Änderung — die
 * Vorschau etwa renderte den Zettel danach im Sekundentakt neu, obwohl niemand etwas getippt
 * hatte. Ohne eingehende Änderung steht ohnehin schon alles im Dokument, was hier stünde.
 */
function einarbeiten(antwort: Antwort, gesendet: Aenderung[], gesendetBild: Flachbild) {
    const waehrenddessen = unterschied(gesendetBild, flach(arbeitsmappe))
    serverBild = anlegen(anlegen(serverBild, gesendet), antwort.aenderungen)

    verbindung.stand = antwort.stand
    verbindung.zuletzt = Date.now()
    if (!antwort.aenderungen.length) return
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
            `/api/sitzung/${verbindung.token}/aenderungen`,
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
 * Verbindet mit einer Sitzung. Was auf dem Bildschirm steht, wird durch das ersetzt, was die
 * Sitzung hält — sie wird nicht mit dem zusammengeführt, was zufällig in diesem Browser lag,
 * sonst landen die Reste des einen bei allen anderen.
 */
export async function beitreten(token: string, wer: string) {
    // Fetched before anything is thrown away, so a workspace that cannot be reached leaves this
    // browser with what it had.
    const {data} = await client.get<Antwort>(
        `/api/sitzung/${token}/aenderungen`, {params: {seit: 0}})

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
