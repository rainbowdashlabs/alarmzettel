import {reactive, watch} from 'vue'
import {neuSortieren} from '../scripts/listen'
import {
    ARBEITSMAPPE_VERSION,
    naechste,
    leereArbeitsmappe,
    leererAlarm,
    type Alarm,
    type Arbeitsmappe,
} from '../interfaces/Alarm'

const STORAGE_KEY = 'alarmzettel_arbeitsmappe'

function laden(): Arbeitsmappe {
    try {
        const roh = localStorage.getItem(STORAGE_KEY)
        if (roh) return uebernehmen(JSON.parse(roh))
    } catch { /* a blocked or corrupt store simply starts empty */ }
    return leereArbeitsmappe()
}

/** Fills in whatever an older or hand-edited file leaves out, so the editor never sees holes. */
export function uebernehmen(roh: unknown): Arbeitsmappe {
    const leer = leereArbeitsmappe()
    const quelle = (roh ?? {}) as Partial<Arbeitsmappe> & {kataloge?: {funkrufnamen?: string[]}}
    const kataloge = {...leer.kataloge, ...(quelle.kataloge ?? {})}

    // A file written before vehicles carried their strength lists bare Funkrufnamen.
    const alteNamen = quelle.kataloge?.funkrufnamen
    if (Array.isArray(alteNamen) && !quelle.kataloge?.fahrzeuge?.length) {
        kataloge.fahrzeuge = alteNamen.map(funkrufname => ({funkrufname, staerke: '', ezp: '', status: ''}))
    }

    return sortierungSetzen({
        version: ARBEITSMAPPE_VERSION,
        alarme: (quelle.alarme ?? []).map(alarm => ({...leererAlarm(), ...alarm})),
        kataloge,
    })
}

/**
 * Numbers every list by its current position. A file states its order by the order of its lists,
 * not by a sort key; left alone the entries would come back ordered by their random ids.
 */
function sortierungSetzen(mappe: Arbeitsmappe): Arbeitsmappe {
    mappe.alarme.forEach((alarm, stelle) => {
        alarm.sortierung = stelle
        alarm.hinweise.forEach((hinweis, platz) => (hinweis.sortierung = platz))
        alarm.einsatzmittel.forEach((gruppe, platz) => {
            gruppe.sortierung = platz
            gruppe.fahrzeuge.forEach((fahrzeug, rang) => (fahrzeug.sortierung = rang))
        })
    })
    return mappe
}

export const arbeitsmappe = reactive<Arbeitsmappe>(laden())

watch(arbeitsmappe, (wert) => {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(wert))
    } catch { /* nothing to do if the browser refuses to store */ }
}, {deep: true})

export function ersetzen(neu: Arbeitsmappe) {
    arbeitsmappe.version = neu.version
    arbeitsmappe.alarme = neu.alarme
    arbeitsmappe.kataloge = neu.kataloge
}

export function alarmAnlegen(): Alarm {
    const alarm = leererAlarm()
    alarm.sortierung = naechste(arbeitsmappe.alarme)
    alarm.einsatzNr = String(arbeitsmappe.alarme.length)
    arbeitsmappe.alarme.push(alarm)
    return alarm
}

export function alarmKopieren(id: string): Alarm | undefined {
    const vorlage = alarmFinden(id)
    if (!vorlage) return undefined
    const kopie: Alarm = JSON.parse(JSON.stringify(vorlage))
    kopie.id = crypto.randomUUID()
    kopie.sortierung = vorlage.sortierung + 0.5
    kopie.einsatzNr = String(arbeitsmappe.alarme.length)
    // Copied entries need their own identity, or the merge would treat them as the originals.
    for (const hinweis of kopie.hinweise) hinweis.id = crypto.randomUUID()
    for (const gruppe of kopie.einsatzmittel) {
        gruppe.id = crypto.randomUUID()
        for (const fahrzeug of gruppe.fahrzeuge) fahrzeug.id = crypto.randomUUID()
    }
    arbeitsmappe.alarme.splice(arbeitsmappe.alarme.indexOf(vorlage) + 1, 0, kopie)
    return kopie
}

export function alarmLoeschen(id: string) {
    const index = arbeitsmappe.alarme.findIndex(alarm => alarm.id === id)
    if (index >= 0) arbeitsmappe.alarme.splice(index, 1)
}

export function alarmVerschieben(id: string, richtung: -1 | 1) {
    neuSortieren(arbeitsmappe.alarme, arbeitsmappe.alarme.findIndex(alarm => alarm.id === id), richtung)
}

export function alarmFinden(id: string): Alarm | undefined {
    return arbeitsmappe.alarme.find(alarm => alarm.id === id)
}

/** The catalogue lists that are plain words; vehicles carry more than a name and are separate. */
type Wortliste = Extract<keyof Arbeitsmappe['kataloge'], 'stichwoerter' | 'status' | 'trupp'>

/**
 * Suggestions for a field: what the user put in the catalogue, plus whatever already appears
 * elsewhere in the working set, so a value typed once is offered the next time.
 */
export function vorschlaege(katalog: Wortliste,
                            gelesen: (alarm: Alarm) => string[]): string[] {
    const gesehen = arbeitsmappe.alarme.flatMap(gelesen)
    const alle = [...arbeitsmappe.kataloge[katalog], ...gesehen]
    return [...new Set(alle.map(wert => wert.trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'de'))
}

export function stichwortVorschlaege(): string[] {
    return vorschlaege('stichwoerter', alarm => [alarm.stichwort])
}

export function funkrufnameVorschlaege(): string[] {
    const ausKatalog = arbeitsmappe.kataloge.fahrzeuge.map(vorlage => vorlage.funkrufname)
    const benutzt = arbeitsmappe.alarme.flatMap(alarm =>
        alarm.einsatzmittel.flatMap(gruppe => gruppe.fahrzeuge.map(fahrzeug => fahrzeug.funkrufname)))
    return [...new Set([...ausKatalog, ...benutzt].map(wert => wert.trim()).filter(Boolean))]
        .sort((a, b) => a.localeCompare(b, 'de'))
}

/** The catalogue entry for a Funkrufname, so picking a vehicle can bring its defaults along. */
export function fahrzeugvorlage(funkrufname: string) {
    const gesucht = funkrufname.trim().toLowerCase()
    return arbeitsmappe.kataloge.fahrzeuge.find(
        vorlage => vorlage.funkrufname.trim().toLowerCase() === gesucht)
}

export function statusVorschlaege(): string[] {
    return vorschlaege('status', alarm =>
        alarm.einsatzmittel.flatMap(gruppe => gruppe.fahrzeuge.map(fahrzeug => fahrzeug.status)))
}

export function truppVorschlaege(): string[] {
    return vorschlaege('trupp', alarm =>
        alarm.einsatzmittel.flatMap(gruppe => gruppe.fahrzeuge.map(fahrzeug => fahrzeug.trupp)))
}
