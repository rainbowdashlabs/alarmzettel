/**
 * Anything that sits in a list carries an id and a sort key. Two people editing one Alarm touch
 * different entries far more often than the same one, so the merge works per entry — which needs
 * an identity that survives a reorder. The sort key is fractional: an entry moved between two
 * others takes the value between theirs, so moving one thing never rewrites the rest.
 */
export interface Eintrag {
    id: string
    sortierung: number
}

export interface Adresse {
    strasse: string
    hnr: string
    objekt: string
    plz: string
    ort: string
}

export interface Karte {
    kab: string
    fwPlan: string
    ePlan: string
    polarKoordinaten: string
}

export interface Fahrzeug extends Eintrag {
    /** The catalogue entry this stands for, if any. Empty where the Funkrufname was typed. */
    vorlageId: string
    funkrufname: string
    ezp: string
    status: string
    staerke: string
    trupp: string
    hinweis: string
    /** The vehicle this sheet is addressed to — printed on grey, and only ever one per Alarm. */
    alarmFuer: boolean
}

export interface Einsatzmittelgruppe extends Eintrag {
    gruppe: string
    fahrzeuge: Fahrzeug[]
}

export interface HinweisText extends Eintrag {
    typ: 'text'
    text: string
}

/** A dispatch code together with the path taken to reach it, as printed after the code. */
export interface HinweisCode extends Eintrag {
    typ: 'code'
    code: string
    meldung: string
    antworten: string[]
}

export type Hinweis = HinweisText | HinweisCode

export interface Alarm extends Eintrag {
    behoerde: string
    titel: string
    einsatzNr: string
    einsatzDatum: string
    einsatzZeit: string
    meldungDatum: string
    meldungZeit: string
    aPlatz: string
    polizei: string
    sonderrechte: string
    arbeitsgruppe: string
    wachalarmNr: string
    /** The catalogue entry this stands for, if any. Empty where the Stichwort was typed. */
    stichwortId: string
    stichwort: string
    kurzinfo: string
    anfahrtsadresse: Adresse
    einsatzadresse: Adresse
    karte: Karte
    meldungsquelle: string
    rueckrufnummer: string
    anrufer: string
    betroffener: string
    meldender: string
    wasIstPassiert: string
    hinweise: Hinweis[]
    einsatzmittel: Einsatzmittelgruppe[]
}

/** A vehicle as the station keeps it: picking it brings its strength, EZP and status along. */
export interface Fahrzeugvorlage {
    /** What an Alarm points at, so renaming the vehicle reaches every sheet that uses it. */
    id: string
    funkrufname: string
    staerke: string
    ezp: string
    status: string
    /** Wie viele Köpfe hineinpassen. Nur für den Ablaufplan; der Alarmzettel kennt das nicht. */
    plaetze: string
    /** Welche Fahrerlaubnisklasse es verlangt, gegen `Person.fahrerlaubnis` geprüft. */
    fuehrerschein: string
}

/** A Stichwort is only its text, so the id is the whole reason an Alarm can follow a rename. */
export interface Stichwortvorlage {
    id: string
    text: string
}

export interface Kataloge {
    stichwoerter: Stichwortvorlage[]
    fahrzeuge: Fahrzeugvorlage[]
    status: string[]
    trupp: string[]
    /** One fixed value for the whole working set; every new Alarm starts with it. */
    arbeitsgruppe: string
    /** The station the sheets are written for. The Polar-Koordinaten are measured from it. */
    wache: Adresse
}

export interface Arbeitsmappe {
    version: number
    alarme: Alarm[]
    kataloge: Kataloge
    /** Der Ablaufplan. Abschaltbar und ohne Wirkung auf den Alarmzettel, solange er aus ist. */
    planung: Planung
}

import {aPlatzKennung, festnetznummer, mobilnummer, zufallsname} from '../scripts/generator'
import {leerePlanung, type Planung} from './Planung'

export const ARBEITSMAPPE_VERSION = 1

export function leereAdresse(): Adresse {
    return {strasse: '', hnr: '', objekt: '', plz: '', ort: ''}
}

/** New entries go to the end; `naechste` reads the highest sort key already in the list. */
export function naechste(eintraege: Eintrag[]): number {
    return eintraege.reduce((groesste, eintrag) => Math.max(groesste, eintrag.sortierung), -1) + 1
}

export function leeresFahrzeug(sortierung = 0): Fahrzeug {
    return {
        id: crypto.randomUUID(), sortierung, vorlageId: '',
        funkrufname: '', ezp: '', status: '', staerke: '', trupp: '', hinweis: '', alarmFuer: false,
    }
}

export function leereGruppe(sortierung = 0): Einsatzmittelgruppe {
    return {
        id: crypto.randomUUID(), sortierung,
        gruppe: 'keine Gruppe',
        fahrzeuge: [leeresFahrzeug()],
    }
}

export function leererHinweisText(sortierung = 0): HinweisText {
    return {id: crypto.randomUUID(), sortierung, typ: 'text', text: ''}
}

export function leererHinweisCode(sortierung = 0): HinweisCode {
    return {id: crypto.randomUUID(), sortierung, typ: 'code', code: '', meldung: '', antworten: []}
}

/** The Stichwörter the Berlin AAO uses, as the starting point for a fresh working set. */
export const STICHWOERTER = [
    'BRAND 1', 'BRAND 2', 'BRAND 3', 'BRAND 4', 'BRAND 6', 'BRAND 8', 'BRAND 10',
    'BRAND K.', 'BRAND M.',
    'TH 1', 'TH 2', 'TH 3', 'TH K.', 'TH M.',
]

export function stichwortvorlagen(): Stichwortvorlage[] {
    return STICHWOERTER.map(text => ({id: crypto.randomUUID(), text}))
}

export function leererAlarm(): Alarm {
    const heute = new Date()
    const datum = heute.toLocaleDateString('de-DE')
    const zeit = heute.toLocaleTimeString('de-DE', {hour: '2-digit', minute: '2-digit'})
    return {
        id: crypto.randomUUID(),
        sortierung: 0,
        behoerde: 'Berliner Feuerwehr',
        titel: 'Alarm für',
        einsatzNr: '',
        einsatzDatum: datum,
        einsatzZeit: zeit,
        meldungDatum: datum,
        meldungZeit: zeit,
        aPlatz: aPlatzKennung(),
        stichwortId: '',
        polizei: 'N',
        sonderrechte: 'J',
        arbeitsgruppe: '',
        wachalarmNr: '',
        stichwort: '',
        kurzinfo: '',
        anfahrtsadresse: leereAdresse(),
        einsatzadresse: leereAdresse(),
        karte: {kab: '', fwPlan: '', ePlan: '', polarKoordinaten: ''},
        meldungsquelle: festnetznummer(),
        rueckrufnummer: mobilnummer(),
        anrufer: zufallsname(),
        betroffener: '',
        meldender: '',
        wasIstPassiert: '',
        hinweise: [],
        einsatzmittel: [leereGruppe()],
    }
}

export function leereArbeitsmappe(): Arbeitsmappe {
    return {
        version: ARBEITSMAPPE_VERSION,
        alarme: [],
        planung: leerePlanung(),
        kataloge: {
            stichwoerter: stichwortvorlagen(), fahrzeuge: [], status: [], trupp: [],
            arbeitsgruppe: '', wache: leereAdresse(),
        },
    }
}
