/**
 * Der Ablaufplan in der Arbeitsmappe: anlegen, entfernen, nachschlagen.
 *
 * Die Kette selbst — Läufe und Schritte — kommt später; hier stehen erst die Stammdaten, auf die
 * sie sich beziehen wird.
 */
import {arbeitsmappe} from './arbeitsmappe'
import {naechste, leereAdresse} from '../interfaces/Alarm'
import type {Ort, Person, Tag, Verfuegbarkeit} from '../interfaces/Planung'

export function planung() {
    return arbeitsmappe.planung
}

export function planungUmschalten(an: boolean) {
    arbeitsmappe.planung.aktiv = an
}

export function tagAnlegen(): Tag {
    const tag: Tag = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.planung.tage),
        datum: new Date().toISOString().slice(0, 10), name: '',
    }
    arbeitsmappe.planung.tage.push(tag)
    return tag
}

export function ortAnlegen(): Ort {
    const ort: Ort = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.planung.orte),
        name: '', adresse: leereAdresse(),
    }
    arbeitsmappe.planung.orte.push(ort)
    return ort
}

export function personAnlegen(): Person {
    const person: Person = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.planung.personen),
        name: '', rollen: [], fahrerlaubnis: [], anzahl: 1, verfuegbar: [],
    }
    arbeitsmappe.planung.personen.push(person)
    return person
}

/**
 * Ein Fenster, in dem jemand da ist. Wer keines hat, ist immer da — deshalb legt das erste
 * Fenster den ganzen ersten Tag an und wird von dort aus zurechtgezogen.
 */
export function verfuegbarkeitAnlegen(person: Person): Verfuegbarkeit {
    const tag = arbeitsmappe.planung.tage[0]?.datum ?? new Date().toISOString().slice(0, 10)
    const fenster: Verfuegbarkeit = {
        id: crypto.randomUUID(), sortierung: naechste(person.verfuegbar),
        von: `${tag}T08:00`, bis: `${tag}T18:00`,
    }
    person.verfuegbar.push(fenster)
    return fenster
}

export function entfernen<T>(liste: T[], eintrag: T) {
    const stelle = liste.indexOf(eintrag)
    if (stelle >= 0) liste.splice(stelle, 1)
}

/** Ein Wort in einer Liste an- oder abwählen — Rollen und Fahrerlaubnisklassen einer Person. */
export function umschalten(liste: string[], wert: string) {
    const stelle = liste.indexOf(wert)
    if (stelle >= 0) liste.splice(stelle, 1)
    else liste.push(wert)
}

export function wortHinzufuegen(liste: string[], wert: string) {
    const sauber = wert.trim()
    if (sauber && !liste.includes(sauber)) liste.push(sauber)
}

export function ortName(ortId: string): string {
    return arbeitsmappe.planung.orte.find(ort => ort.id === ortId)?.name ?? ''
}

export function personName(personId: string): string {
    return arbeitsmappe.planung.personen.find(person => person.id === personId)?.name ?? ''
}

/** Wie viele Köpfe an Bord dürfen. Leer heißt: unbekannt, dann wird nicht gezählt. */
export function plaetze(fahrzeugId: string): number | null {
    const roh = arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === fahrzeugId)?.plaetze?.trim()
    return roh && /^\d+$/.test(roh) ? Number(roh) : null
}
