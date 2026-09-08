/**
 * Was sich aus den Ketten ergibt: der Plan einer Person, die Sicht auf einen Ort, und die
 * Prüfungen.
 *
 * Gepflegt wird nur die Kette je Fahrzeug und je Person. Alles hier ist gerechnet und wird
 * nirgends gespeichert — zwei Pläne, die sich widersprechen könnten, gibt es damit nicht.
 *
 * Das Modul kennt weder Store noch Vue, damit dieselbe Rechnung die Oberfläche versorgt und in
 * `tools/ablauf_pruefen.mjs` außerhalb eines Browsers geprüft werden kann.
 */
import type {Fahrzeugvorlage} from '../interfaces/Alarm'
import type {Lauf, Person, Planung, Schritt} from '../interfaces/Planung'
import type {Punkt} from './polar'
import {entfernungKm} from './polar'
import {alsMinuten, dauer, ueberschneidet} from './zeit'

/** Minuten je Kilometer Luftlinie. Grobe Schätzung, jederzeit überschreibbar. */
export const MINUTEN_JE_KM: Record<Schritt['mittel'], number> = {fuss: 15, fahrzeug: 3, eigen: 3}

/** Unter diesem Anteil der Schätzung gilt eine Fahrt als zu knapp geplant. */
const KNAPP = 0.6

/**
 * Alles, was die Rechnung braucht. `punkte` sind die Koordinaten der Orte, soweit der
 * Adressdienst sie kennt; ohne sie entfällt allein die Prüfung auf zu knappe Fahrten.
 */
export interface Plandaten {
    planung: Planung
    fahrzeuge: Fahrzeugvorlage[]
    punkte?: Record<string, Punkt>
}

/** Ein Schritt, wie er im Plan einer Person steht — mit dem Lauf, aus dem er stammt. */
export interface Personenschritt {
    lauf: Lauf
    schritt: Schritt
    /** Sie fährt in diesem Schritt selbst. */
    faehrt: boolean
    /** Wo der Schritt anfängt; bei einer Fahrt der Ort des vorigen Schritts. */
    vonOrtId: string
    /** Wo er endet. */
    nachOrtId: string
}

/** Wer und was zu welcher Zeit an einem Ort ist. Fahrten zählen nicht — sie sind dazwischen. */
export interface Ortsbelegung {
    lauf: Lauf
    schritt: Schritt
    von: string
    bis: string
    personIds: string[]
}

export type Befundart =
    'zuVoll' | 'ohneErlaubnis' | 'ohneFahrer' | 'zweiFahrer' | 'zustiegInsNichts'
    | 'zweiOrte' | 'ausserhalb' | 'zuKnapp' | 'lageLeer'

/**
 * Ein Fund. Nichts davon blockiert die Eingabe: ein Plan darf zwischendurch unfertig sein, und
 * wer nur halbtags kann, soll probeweise einplanbar bleiben.
 */
export interface Befund {
    art: Befundart
    laufId?: string
    schrittId?: string
    personId?: string
    programmpunktId?: string
    /** Zahlen und Namen für die Meldung. */
    werte?: Record<string, string | number>
}

function person(daten: Plandaten, personId: string): Person | undefined {
    return daten.planung.personen.find(p => p.id === personId)
}

function fahrzeug(daten: Plandaten, fahrzeugId: string): Fahrzeugvorlage | undefined {
    return daten.fahrzeuge.find(v => v.id === fahrzeugId)
}

function name(daten: Plandaten, personId: string): string {
    return person(daten, personId)?.name ?? ''
}

/** Wie viele Köpfe eine Zeile bedeutet — „Mimen (4)“ zählt vier. */
function koepfe(daten: Plandaten, personId: string): number {
    return person(daten, personId)?.anzahl || 1
}

/** Wo eine Fahrt losgeht, sagt der vorige Schritt; ein Aufenthalt fängt an, wo er ist. */
export function vonOrt(lauf: Lauf, schritt: Schritt): string {
    if (schritt.art !== 'fahrt') return schritt.ortId
    return lauf.schritte[lauf.schritte.indexOf(schritt) - 1]?.ortId ?? schritt.ortId
}

function nachZeit<T extends { von: string }>(eintraege: T[]): T[] {
    return [...eintraege].sort((a, b) => (alsMinuten(a.von) ?? 0) - (alsMinuten(b.von) ?? 0))
}

/**
 * Der Plan einer Person: alle Fahrzeugschritte, in deren Besatzung sie steht, plus die Schritte
 * ihrer eigenen Kette, nach Zeit sortiert. Er wird nirgends gepflegt, sondern hieraus gelesen.
 */
export function personenplan(daten: Plandaten, personId: string): Personenschritt[] {
    const eintraege: (Personenschritt & { von: string })[] = []
    for (const lauf of daten.planung.laeufe) {
        const eigene = lauf.personId === personId
        for (const schritt of lauf.schritte) {
            const sitzt = schritt.besatzung.find(platz => platz.personId === personId)
            if (!eigene && !sitzt) continue
            eintraege.push({
                lauf, schritt, von: schritt.von,
                faehrt: Boolean(sitzt?.faehrt),
                vonOrtId: vonOrt(lauf, schritt), nachOrtId: schritt.ortId,
            })
        }
    }
    return nachZeit(eintraege)
}

/** Wer und was an diesem Ort steht, nach Zeit sortiert — die Ortssicht. */
export function ortssicht(daten: Plandaten, ortId: string): Ortsbelegung[] {
    const belegungen: Ortsbelegung[] = []
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) {
            if (schritt.art !== 'aufenthalt' || schritt.ortId !== ortId) continue
            belegungen.push({
                lauf, schritt, von: schritt.von, bis: schritt.bis,
                personIds: lauf.personId
                    ? [lauf.personId, ...schritt.besatzung.map(platz => platz.personId)]
                    : schritt.besatzung.map(platz => platz.personId),
            })
        }
    }
    return nachZeit(belegungen)
}

/**
 * Die Prüfungen, die an einem einzelnen Schritt hängen: Plätze, Fahrerlaubnis, Fahrer und die
 * Fahrzeit. Die Oberfläche zeigt sie am Schritt, `pruefen` sammelt sie über den ganzen Plan.
 */
export function schrittBefunde(daten: Plandaten, lauf: Lauf, schritt: Schritt): Befund[] {
    const befunde: Befund[] = []
    const stelle = {laufId: lauf.id, schrittId: schritt.id}
    const wagen = fahrzeug(daten, lauf.fahrzeugId)

    const grenze = wagen?.plaetze?.trim()
    if (grenze && /^\d+$/.test(grenze)) {
        const besetzt = schritt.besatzung
            .reduce((summe, platz) => summe + koepfe(daten, platz.personId), 0)
        if (besetzt > Number(grenze)) {
            befunde.push({art: 'zuVoll', ...stelle, werte: {plaetze: Number(grenze), koepfe: besetzt}})
        }
    }

    const fahrer = schritt.besatzung.filter(platz => platz.faehrt)
    if (lauf.fahrzeugId && schritt.art === 'fahrt') {
        if (fahrer.length === 0) befunde.push({art: 'ohneFahrer', ...stelle})
        if (fahrer.length > 1) {
            befunde.push({art: 'zweiFahrer', ...stelle, werte: {anzahl: fahrer.length}})
        }
    }

    const klasse = wagen?.fuehrerschein?.trim()
    if (klasse) {
        for (const platz of fahrer) {
            const wer = person(daten, platz.personId)
            if (wer && !wer.fahrerlaubnis.includes(klasse)) {
                befunde.push({
                    art: 'ohneErlaubnis', ...stelle, personId: wer.id,
                    werte: {wer: wer.name, klasse},
                })
            }
        }
    }

    const geschaetzt = fahrzeitSchaetzung(daten, lauf, schritt)
    const geplant = dauer(schritt.von, schritt.bis)
    if (geschaetzt !== null && geplant !== null && geplant < geschaetzt * KNAPP) {
        befunde.push({art: 'zuKnapp', ...stelle, werte: {geplant, geschaetzt}})
    }
    return befunde
}

/**
 * Geschätzte Fahrzeit dieses Schritts: Luftlinie mal Minuten je Kilometer, auf fünf Minuten
 * gerundet und nie unter fünf. Ohne Koordinaten an einem der beiden Orte gibt es keine Schätzung
 * — die Luftlinie kennt ohnehin weder Spree noch Baustelle.
 */
export function fahrzeitSchaetzung(daten: Plandaten, lauf: Lauf, schritt: Schritt): number | null {
    if (schritt.art !== 'fahrt') return null
    const von = daten.punkte?.[vonOrt(lauf, schritt)]
    const nach = daten.punkte?.[schritt.ortId]
    if (!von || !nach || vonOrt(lauf, schritt) === schritt.ortId) return null
    return Math.max(5, Math.round(entfernungKm(von, nach) * MINUTEN_JE_KM[schritt.mittel] / 5) * 5)
}

/**
 * Zustieg ins Nichts: jemand steht in einem Schritt, war aber unmittelbar davor woanders. Das
 * ist die Abholung, die nicht aufgeht — und der Fahrerwechsel am falschen Ort ist derselbe Fall.
 */
function zustiegBefunde(daten: Plandaten, personId: string, plan: Personenschritt[]): Befund[] {
    const befunde: Befund[] = []
    for (let stelle = 1; stelle < plan.length; stelle++) {
        const vorher = plan[stelle - 1]!
        const jetzt = plan[stelle]!
        if (vorher.nachOrtId === jetzt.vonOrtId) continue
        if (ueberschneidet(vorher.schritt.von, vorher.schritt.bis,
                           jetzt.schritt.von, jetzt.schritt.bis)) continue
        befunde.push({
            art: 'zustiegInsNichts', personId,
            laufId: jetzt.lauf.id, schrittId: jetzt.schritt.id,
            werte: {wer: name(daten, personId)},
        })
    }
    return befunde
}

/** Dieselbe Person zur selben Zeit in zwei Ketten. */
function doppelBefunde(daten: Plandaten, personId: string, plan: Personenschritt[]): Befund[] {
    const befunde: Befund[] = []
    for (let a = 0; a < plan.length; a++) {
        for (let b = a + 1; b < plan.length; b++) {
            const eins = plan[a]!, zwei = plan[b]!
            if (eins.lauf.id === zwei.lauf.id) continue
            if (!ueberschneidet(eins.schritt.von, eins.schritt.bis,
                                zwei.schritt.von, zwei.schritt.bis)) continue
            befunde.push({
                art: 'zweiOrte', personId,
                laufId: zwei.lauf.id, schrittId: zwei.schritt.id,
                werte: {wer: name(daten, personId)},
            })
        }
    }
    return befunde
}

/** Nichts eingetragen heißt immer da; sonst muss der Schritt in ein Fenster passen. */
function ausserhalbBefunde(wer: Person, plan: Personenschritt[]): Befund[] {
    if (wer.verfuegbar.length === 0) return []
    return plan
        .filter(eintrag => !wer.verfuegbar.some(fenster =>
            (alsMinuten(fenster.von) ?? 0) <= (alsMinuten(eintrag.schritt.von) ?? 0) &&
            (alsMinuten(fenster.bis) ?? 0) >= (alsMinuten(eintrag.schritt.bis) ?? 0)))
        .map(eintrag => ({
            art: 'ausserhalb' as const, personId: wer.id,
            laufId: eintrag.lauf.id, schrittId: eintrag.schritt.id,
            werte: {wer: wer.name},
        }))
}

/** Alle Prüfungen über den ganzen Plan. */
export function pruefen(daten: Plandaten): Befund[] {
    const befunde: Befund[] = []
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) befunde.push(...schrittBefunde(daten, lauf, schritt))
    }
    for (const wer of daten.planung.personen) {
        const plan = personenplan(daten, wer.id)
        befunde.push(...zustiegBefunde(daten, wer.id, plan))
        befunde.push(...doppelBefunde(daten, wer.id, plan))
        befunde.push(...ausserhalbBefunde(wer, plan))
    }
    const benutzt = new Set(daten.planung.laeufe
        .flatMap(lauf => lauf.schritte.map(schritt => schritt.programmpunktId)))
    for (const punkt of daten.planung.programmpunkte) {
        if (!benutzt.has(punkt.id)) {
            befunde.push({art: 'lageLeer', programmpunktId: punkt.id, werte: {was: punkt.name}})
        }
    }
    return befunde
}
