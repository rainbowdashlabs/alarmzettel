/**
 * Der Ablaufplan eines Übungstages.
 *
 * Geplant wird als Kette: ein Fahrzeug oder eine Person hat eine Folge von Schritten, und jeder
 * fängt an, wo der vorige aufgehört hat. Der Startort einer Fahrt wird deshalb nirgends
 * gespeichert — er steht schon fest, und ein Sprung von A nach B ohne Weg dazwischen ist nicht
 * darstellbar statt nur falsch.
 *
 * Der Personenplan wird aus denselben Daten gerechnet und nirgends gepflegt: alle Schritte, in
 * deren Besatzung jemand steht, plus die eigenen. Zwei Pläne, die sich widersprechen könnten,
 * gibt es damit nicht.
 */
import type {Adresse, Eintrag} from './Alarm'

/** Ein Tag der Veranstaltung. Eigene Liste, damit auch ein noch leerer Tag angelegt sein kann. */
export interface Tag extends Eintrag {
    /** ISO, `2026-09-19`. */
    datum: string
    name: string
}

/**
 * Ein eingetragener Ort mit einer Identität — kein Text in einer Zelle. Nur dadurch ist „am
 * selben Ort zur selben Zeit“ überhaupt entscheidbar, woran Fahrerwechsel, Zustieg und Übergabe
 * hängen.
 *
 * Orte stehen im Katalog: sie gehören der Wache und überdauern den einzelnen Übungstag.
 */
export interface Ort extends Eintrag {
    name: string
    adresse: Adresse
}

/** Die Kennung des Orts, der die eigene Wache ist. Er wird nicht angelegt, es gibt ihn. */
export const DIENSTSTELLE = 'wache'

/** Ein Zeitfenster, in dem jemand überhaupt da ist. Keines eingetragen heißt: immer. */
export interface Verfuegbarkeit extends Eintrag {
    /** ISO mit Uhrzeit, `2026-09-19T10:00`. */
    von: string
    bis: string
}

export interface Person extends Eintrag {
    name: string
    rollen: string[]
    /** Führerscheinklassen, gegen `Fahrzeugvorlage.fuehrerschein` geprüft. */
    fahrerlaubnis: string[]
    /** Wie viele Köpfe diese Zeile bedeutet — „Mimen (4)“ belegt vier Plätze. */
    anzahl: number
    verfuegbar: Verfuegbarkeit[]
}

/**
 * Die Lage als solche, ohne Zeiten, ohne Ort und ohne Teilnehmer: wann sie läuft, wo sie
 * stattfindet und wer dabei ist, sagen die Schritte, die auf sie zeigen. So kann sie sich nicht
 * selbst widersprechen, und zwei Fahrzeuge an derselben Lage teilen sich einen Eintrag.
 */
export interface Programmpunkt extends Eintrag {
    name: string
    /** Der Alarm, der zu dieser Lage gehört. Leer, wenn es keiner ist — Frühstück etwa. */
    alarmId: string
}

/** Womit es zwischen zwei Orten weitergeht. */
export type Mittel = 'fahrzeug' | 'fuss' | 'eigen'

export interface Besatzung extends Eintrag {
    personId: string
    faehrt: boolean
}

/**
 * Ein Stück Material, das in diesem Schritt dabei ist. Es hängt am Schritt wie die Besatzung —
 * dadurch sagt der Plan von selbst, wo etwas liegt und womit es wohin gefahren wird.
 */
export interface Materialposten extends Eintrag {
    materialId: string
    /** Wie viele Stück davon. Eins, solange niemand etwas anderes sagt. */
    anzahl: number
}

/**
 * Ein Schritt einer Kette: entweder an einem Ort sein, oder zu einem fahren. Die Besatzung ist
 * die vollständige Liste für diesen Schritt, nicht die Änderung gegenüber dem vorigen — dadurch
 * ist jeder Schritt für sich lesbar und jede Prüfung eine Frage an einen einzelnen Schritt.
 */
export interface Schritt extends Eintrag {
    art: 'aufenthalt' | 'fahrt'
    /** Womit es hergeht — beim Aufenthalt für die erzeugte Anfahrt, bei der Fahrt für sie selbst. */
    mittel: Mittel
    /** Minuten für die erzeugte Anfahrt. Null heißt: die Schätzung gilt. */
    fahrzeit: number
    von: string
    bis: string
    /** Wo man ist, beziehungsweise wohin es geht. Woher, sagt der vorige Schritt. */
    ortId: string
    programmpunktId: string
    /** Was sonst zu diesem Schritt zu sagen ist — für alles, wofür es kein Feld gibt. */
    notiz: string
    /**
     * Ob dieses Fahrzeug zum Einsatzmittelaufgebot der Lage gehört. Wer nur Mimen hinbringt,
     * steht am Ort, ohne alarmiert zu sein — und bekommt weder einen Zettel noch eine Zeile
     * darauf.
     */
    aufgebot: boolean
    besatzung: Besatzung[]
    material: Materialposten[]
}

/** Die Kette eines Fahrzeugs oder einer Person. Genau eines von beiden ist gesetzt. */
export interface Lauf extends Eintrag {
    fahrzeugId: string
    personId: string
    schritte: Schritt[]
}

/**
 * Der Plan eines Übungstages: die Lagen und die Ketten.
 *
 * Was die Wache dauerhaft führt — Tage, Personal, Rollen, Fahrerlaubnisklassen, Orte und
 * Material — steht im Katalog und nicht hier.
 */
export interface Planung {
    /** Aus: kein Navigationspunkt, keine Daten, der Alarmzettel-Teil unverändert. */
    aktiv: boolean
    programmpunkte: Programmpunkt[]
    laeufe: Lauf[]
}

export function leerePlanung(): Planung {
    return {aktiv: false, programmpunkte: [], laeufe: []}
}

export const ROLLEN = ['Ausbilder', 'Teilnehmer', 'Mime', 'Foto', 'Beobachter']
export const FAHRERLAUBNISSE = ['B', 'BE', 'C1', 'C1E', 'C', 'CE']
