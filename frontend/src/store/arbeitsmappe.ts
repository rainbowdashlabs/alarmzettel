import {reactive, watch} from 'vue'
import {freigabeVergessen} from './freigabe'
import {fahrzeugwerte} from '../scripts/katalog'
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
        kataloge.fahrzeuge = alteNamen.map(funkrufname =>
            ({id: crypto.randomUUID(), funkrufname, staerke: '', ezp: '', status: ''}))
    }

    // A file written before either catalogue had an identity of its own: Stichwörter were bare
    // strings and vehicles were known by their Funkrufname. Both get an id here, and the Alarme
    // that use them are pointed at it, so a later rename reaches the sheets that were already
    // written. Matching on the text is only safe this once — from now on the id is the link.
    kataloge.stichwoerter = (kataloge.stichwoerter ?? []).map(eintrag =>
        typeof eintrag === 'string'
            ? {id: crypto.randomUUID(), text: eintrag}
            : {...eintrag, id: eintrag.id || crypto.randomUUID()})
    kataloge.fahrzeuge = kataloge.fahrzeuge.map(vorlage =>
        ({...vorlage, id: vorlage.id || crypto.randomUUID()}))

    return sortierungSetzen(katalogVerknuepfen(verweiseHerstellen({
        version: ARBEITSMAPPE_VERSION,
        alarme: (quelle.alarme ?? []).map(alarm => ({...leererAlarm(), ...alarm})),
        kataloge,
    })))
}

/** Points an Alarm at the catalogue entry whose text it already carries, where it has none yet. */
function verweiseHerstellen(mappe: Arbeitsmappe): Arbeitsmappe {
    const nachText = <T extends {id: string}>(eintraege: T[], lesen: (eintrag: T) => string) =>
        new Map(eintraege.filter(e => lesen(e).trim())
            .map(e => [lesen(e).trim().toLowerCase(), e.id]))
    const stichwoerter = nachText(mappe.kataloge.stichwoerter, e => e.text)
    const fahrzeuge = nachText(mappe.kataloge.fahrzeuge, v => v.funkrufname)

    for (const alarm of mappe.alarme) {
        if (!alarm.stichwortId) {
            alarm.stichwortId = stichwoerter.get(alarm.stichwort.trim().toLowerCase()) ?? ''
        }
        for (const gruppe of alarm.einsatzmittel ?? []) {
            for (const fahrzeug of gruppe.fahrzeuge ?? []) {
                if (fahrzeug.vorlageId) continue
                fahrzeug.vorlageId = fahrzeuge.get(fahrzeug.funkrufname.trim().toLowerCase()) ?? ''
            }
        }
    }
    return mappe
}

/**
 * A working set written before vehicles referred to the catalogue carries its values copied into
 * every Alarm. Clearing the ones that still match turns those copies back into references
 * without changing a single printed sheet — the value is the same either way, it just starts
 * following the catalogue again. Anything that differs was meant as an override and stays.
 */
function katalogVerknuepfen(mappe: Arbeitsmappe): Arbeitsmappe {
    const vorlagen = new Map(mappe.kataloge.fahrzeuge
        .filter(vorlage => vorlage.funkrufname.trim())
        .map(vorlage => [vorlage.funkrufname.trim().toLowerCase(), vorlage]))
    if (!vorlagen.size) return mappe

    for (const alarm of mappe.alarme) {
        for (const gruppe of alarm.einsatzmittel ?? []) {
            for (const fahrzeug of gruppe.fahrzeuge ?? []) {
                const vorlage = vorlagen.get(fahrzeug.funkrufname.trim().toLowerCase())
                if (!vorlage) continue
                for (const feld of ['ezp', 'status', 'staerke'] as const) {
                    if (fahrzeug[feld] && fahrzeug[feld] === vorlage[feld]) fahrzeug[feld] = ''
                }
                const abgeleitet = fahrzeugwerte({...fahrzeug, trupp: ''}, vorlage).trupp
                if (fahrzeug.trupp && fahrzeug.trupp === abgeleitet) fahrzeug.trupp = ''
            }
        }
    }
    return mappe
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

/** A different working set is not the one behind the old link, so the link is not offered for it. */
export function ersetzen(neu: Arbeitsmappe) {
    freigabeVergessen()
    arbeitsmappe.version = neu.version
    arbeitsmappe.alarme = neu.alarme
    arbeitsmappe.kataloge = neu.kataloge
}

export function alarmAnlegen(): Alarm {
    const alarm = leererAlarm()
    alarm.sortierung = naechste(arbeitsmappe.alarme)
    alarm.einsatzNr = String(arbeitsmappe.alarme.length)
    alarm.arbeitsgruppe = arbeitsmappe.kataloge.arbeitsgruppe
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

/** The catalogue lists that are plain words; the two that Alarme point at are separate. */
type Wortliste = Extract<keyof Arbeitsmappe['kataloge'], 'status' | 'trupp'>

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
    const ausKatalog = arbeitsmappe.kataloge.stichwoerter.map(eintrag => eintrag.text)
    const benutzt = arbeitsmappe.alarme.map(alarm => alarm.stichwort)
    return [...new Set([...ausKatalog, ...benutzt].map(wert => wert.trim()).filter(Boolean))]
        .sort((a, b) => a.localeCompare(b, 'de'))
}

/** The catalogue entry an Alarm points at, or the one whose text it matches. */
export function stichwortvorlage(alarm: Alarm) {
    if (alarm.stichwortId) {
        const gefunden = arbeitsmappe.kataloge.stichwoerter.find(e => e.id === alarm.stichwortId)
        if (gefunden) return gefunden
    }
    const gesucht = alarm.stichwort.trim().toLowerCase()
    return arbeitsmappe.kataloge.stichwoerter.find(e => e.text.trim().toLowerCase() === gesucht)
}

/** The id of the catalogue entry reading exactly like this, so picking one links to it. */
export function stichwortIdFuer(text: string): string {
    const gesucht = text.trim().toLowerCase()
    return arbeitsmappe.kataloge.stichwoerter
        .find(eintrag => eintrag.text.trim().toLowerCase() === gesucht)?.id ?? ''
}

/**
 * The catalogue entry for this Stichwort, adding it if it is new. A word typed for the first
 * time joins the catalogue, so it is offered next time and can be corrected in one place later —
 * which only works if the Alarm points at an entry rather than merely spelling the same word.
 */
export function stichwortSichern(text: string): string {
    const sauber = text.trim()
    if (!sauber) return ''
    const vorhanden = stichwortIdFuer(sauber)
    if (vorhanden) return vorhanden
    const eintrag = {id: crypto.randomUUID(), text: sauber}
    arbeitsmappe.kataloge.stichwoerter.push(eintrag)
    return eintrag.id
}

export function funkrufnameVorschlaege(): string[] {
    const ausKatalog = arbeitsmappe.kataloge.fahrzeuge.map(vorlage => vorlage.funkrufname)
    const benutzt = arbeitsmappe.alarme.flatMap(alarm =>
        alarm.einsatzmittel.flatMap(gruppe => gruppe.fahrzeuge.map(fahrzeug => fahrzeug.funkrufname)))
    return [...new Set([...ausKatalog, ...benutzt].map(wert => wert.trim()).filter(Boolean))]
        .sort((a, b) => a.localeCompare(b, 'de'))
}

/**
 * The catalogue entry a vehicle stands for: the one it points at, or failing that the one whose
 * Funkrufname it reads like — a vehicle typed by hand or imported from a spreadsheet has no id.
 */
export function fahrzeugvorlage(fahrzeug: {vorlageId?: string, funkrufname: string}) {
    if (fahrzeug.vorlageId) {
        const gefunden = arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === fahrzeug.vorlageId)
        if (gefunden) return gefunden
    }
    const gesucht = fahrzeug.funkrufname.trim().toLowerCase()
    return arbeitsmappe.kataloge.fahrzeuge.find(
        vorlage => vorlage.funkrufname.trim().toLowerCase() === gesucht)
}

/** The id of the catalogue vehicle named exactly this, so picking one links to it. */
export function fahrzeugIdFuer(funkrufname: string): string {
    const gesucht = funkrufname.trim().toLowerCase()
    return arbeitsmappe.kataloge.fahrzeuge
        .find(vorlage => vorlage.funkrufname.trim().toLowerCase() === gesucht)?.id ?? ''
}

/** As with a Stichwort: a Funkrufname written for the first time joins the catalogue. */
export function fahrzeugSichern(funkrufname: string): string {
    const sauber = funkrufname.trim()
    if (!sauber) return ''
    const vorhanden = fahrzeugIdFuer(sauber)
    if (vorhanden) return vorhanden
    const vorlage = {id: crypto.randomUUID(), funkrufname: sauber,
                     staerke: '', ezp: '', status: ''}
    arbeitsmappe.kataloge.fahrzeuge.push(vorlage)
    return vorlage.id
}

export function statusVorschlaege(): string[] {
    return vorschlaege('status', alarm =>
        alarm.einsatzmittel.flatMap(gruppe => gruppe.fahrzeuge.map(fahrzeug => fahrzeug.status)))
}

export function truppVorschlaege(): string[] {
    return vorschlaege('trupp', alarm =>
        alarm.einsatzmittel.flatMap(gruppe => gruppe.fahrzeuge.map(fahrzeug => fahrzeug.trupp)))
}
