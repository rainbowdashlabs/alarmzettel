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
import type {Fahrzeugvorlage, Materialvorlage} from '../interfaces/Alarm'
import type {Lauf, Mittel, Ort, Person, Planung, Programmpunkt, Schritt} from '../interfaces/Planung'
import type {Punkt} from './polar'
import {entfernungKm} from './polar'
import {alsMinuten, dauer, ueberschneidet, verschieben} from './zeit'

/**
 * Minuten je Kilometer Luftlinie. Grobe Schätzung, jederzeit überschreibbar. Über die eigene
 * Anreise wissen wir nichts, also wird sie nicht geschätzt.
 */
export const MINUTEN_JE_KM: Record<Schritt['mittel'], number> = {fuss: 15, fahrzeug: 3, eigen: 0}

/** Unter diesem Anteil der Schätzung gilt eine Fahrt als zu knapp geplant. */
const KNAPP = 0.6

/**
 * Alles, was die Rechnung braucht. `punkte` sind die Koordinaten der Orte, soweit der
 * Adressdienst sie kennt; ohne sie entfällt allein die Prüfung auf zu knappe Fahrten.
 */
export interface Plandaten {
    planung: Planung
    fahrzeuge: Fahrzeugvorlage[]
    /** Die Orte des Katalogs, die Dienststelle voran. */
    orte: Ort[]
    /** Das Personal des Katalogs — die Ketten zeigen nur auf seine Kennungen. */
    personen: Person[]
    /** Was die Wache an Material führt — wonach die Standorte benannt werden. */
    kataloge?: {material: Materialvorlage[]}
    /** Die Alarme, damit eine Lage den Namen ihres Alarmzettels tragen kann. */
    alarme?: {id: string, stichwort: string}[]
    punkte?: Record<string, Punkt>
}

/** Ein Schritt, wie er im Plan einer Person steht — mit dem Lauf, aus dem er stammt. */
export interface Personenschritt {
    lauf: Lauf
    schritt: Schritt
    /** Sie fährt in diesem Schritt selbst. */
    faehrt: boolean
    /**
     * Wo der Schritt anfängt: bei einer Fahrt der Ort des vorigen Schritts, bei einem Aufenthalt
     * mit erzeugter Anfahrt der Ort, von dem diese Person kommt — stand sie schon am Ziel, ist
     * es das Ziel selbst.
     */
    vonOrtId: string
    /** Wo er endet. */
    nachOrtId: string
    /**
     * Wann sie da ist. Wer die erzeugte Anfahrt mitfährt, ist an deren Ende da; wer schon am Ziel
     * stand, mit dem Beginn des Schritts.
     */
    ankunft: string
}

/**
 * Die Fahrt, die zwischen zwei Aufenthalten von selbst entsteht. Sie wird nirgends gespeichert:
 * woher, sagt der vorige Schritt, wohin dieser, und wie lange es dauert, die Schätzung.
 */
export interface Anfahrt {
    vonOrtId: string
    nachOrtId: string
    von: string
    bis: string
    minuten: number
    mittel: Mittel
}

/** Wer und was zu welcher Zeit an einem Ort ist. Fahrten zählen nicht — sie sind dazwischen. */
export interface Ortsbelegung {
    lauf: Lauf
    schritt: Schritt
    von: string
    bis: string
    personIds: string[]
}

/** Eine Lage, wie sie aus den Schritten entsteht, die auf sie zeigen. */
export interface Lagensicht {
    programmpunkt: Programmpunkt
    /** Wo sie stattfindet — der Ort ihrer Schritte. Leer, wenn keiner zeigt. */
    ortId: string
    /** Früheste Ankunft und spätestes Ende der beteiligten Schritte. Leer, wenn keiner zeigt. */
    von: string
    bis: string
    laeufe: Lauf[]
    personIds: string[]
}

export type Befundart =
    'zuVoll' | 'ohneErlaubnis' | 'ohneFahrer' | 'zweiFahrer' | 'zustiegInsNichts'
    | 'zweiOrte' | 'ausserhalb' | 'zuKnapp' | 'lageLeer' | 'ueberschneidung' | 'zuVielMaterial'
    | 'fahrtFrisstAufenthalt' | 'lageZweiOrte'

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
    return daten.personen.find(eintrag => eintrag.id === personId)
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

/**
 * Wie eine Lage heißt. Zeigt sie auf einen Alarm, ist dessen Stichwort ihr Name — zweimal
 * dasselbe zu pflegen hieße, es widersprüchlich pflegen zu können. Ohne Alarm zählt, was an ihr
 * steht: „Frühstück“ hat kein Stichwort.
 */
export function lagenName(daten: Plandaten, programmpunktId: string): string {
    const punkt = daten.planung.programmpunkte.find(eintrag => eintrag.id === programmpunktId)
    if (!punkt) return ''
    const stichwort = daten.alarme?.find(alarm => alarm.id === punkt.alarmId)?.stichwort
    return stichwort?.trim() || punkt.name
}

/**
 * Wer dieses Fahrzeug fahren darf: die verlangte Klasse steht am Fahrzeug, die vorhandenen an
 * der Person. Verlangt das Fahrzeug keine, darf jeder.
 */
export function darfFahren(daten: Plandaten, fahrzeugId: string, personId: string): boolean {
    const klasse = fahrzeug(daten, fahrzeugId)?.fuehrerschein?.trim()
    if (!klasse) return true
    return Boolean(person(daten, personId)?.fahrerlaubnis.includes(klasse))
}

/** Wo eine Fahrt losgeht, sagt der vorige Schritt; ein Aufenthalt fängt an, wo er ist. */
export function vonOrt(lauf: Lauf, schritt: Schritt): string {
    if (schritt.art !== 'fahrt') return schritt.ortId
    return lauf.schritte[lauf.schritte.indexOf(schritt) - 1]?.ortId ?? schritt.ortId
}

/** Womit dieser Schritt zurückgelegt wird. Eine Fahrzeugkette kennt nur das Fahrzeug. */
export function mittelVon(lauf: Lauf, schritt: Schritt): Mittel {
    return lauf.fahrzeugId ? 'fahrzeug' : schritt.mittel
}

/**
 * Die Fahrt zu diesem Aufenthalt, sofern sie entsteht: der Schritt davor ist ein Aufenthalt an
 * einem anderen Ort. Steht dort eine eingetragene Fahrt, gilt die, und hier entsteht nichts.
 *
 * Sie beginnt, wenn der Aufenthalt beginnt — wer um 7:50 aufbricht und fünf Minuten braucht, ist
 * um 7:55 da. Deshalb ist 7:50 auch die Einsatzzeit des Alarms, der an der Lage hängt.
 */
export function anfahrt(daten: Plandaten, lauf: Lauf, schritt: Schritt): Anfahrt | null {
    if (schritt.art !== 'aufenthalt') return null
    const vorher = lauf.schritte[lauf.schritte.indexOf(schritt) - 1]
    if (!vorher || vorher.art !== 'aufenthalt' || vorher.ortId === schritt.ortId) return null
    const mittel = mittelVon(lauf, schritt)
    const minuten = schritt.fahrzeit
        || schaetzung(daten, vorher.ortId, schritt.ortId, mittel) || 0
    return {
        vonOrtId: vorher.ortId, nachOrtId: schritt.ortId, von: schritt.von,
        bis: verschieben(schritt.von, minuten), minuten, mittel,
    }
}

/** Wann jemand an dem Ort dieses Schritts steht: nach der erzeugten Anfahrt, sonst sofort. */
export function ankunft(daten: Plandaten, lauf: Lauf, schritt: Schritt): string {
    return anfahrt(daten, lauf, schritt)?.bis ?? schritt.von
}

/** Wo eine Lage stattfindet: dort, wo die Schritte stehen, die auf sie zeigen. */
export function lagenOrt(daten: Plandaten, programmpunktId: string): string {
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) {
            if (schritt.programmpunktId === programmpunktId && schritt.art === 'aufenthalt') {
                return schritt.ortId
            }
        }
    }
    return ''
}

function nachZeit<T extends { von: string }>(eintraege: T[]): T[] {
    return [...eintraege].sort((a, b) => (alsMinuten(a.von) ?? 0) - (alsMinuten(b.von) ?? 0))
}

/**
 * Der Plan einer Person: alle Fahrzeugschritte, in deren Besatzung sie steht, plus die Schritte
 * ihrer eigenen Kette, nach Zeit sortiert. Er wird nirgends gepflegt, sondern hieraus gelesen.
 *
 * Die erzeugte Anfahrt fährt nur mit, wer vorher am Startort stand. Wer schon am Ziel wartet —
 * der Mime, der auf das Fahrzeug wartet — steigt dort zu, fährt nicht mit und ist mit dem
 * Beginn des Schritts da.
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
                ankunft: ankunft(daten, lauf, schritt),
            })
        }
    }
    const plan = nachZeit(eintraege)
    for (let stelle = 0; stelle < plan.length; stelle++) {
        const weg = anfahrt(daten, plan[stelle]!.lauf, plan[stelle]!.schritt)
        if (!weg) continue
        if (stelle > 0 && plan[stelle - 1]!.nachOrtId === weg.vonOrtId) {
            plan[stelle]!.vonOrtId = weg.vonOrtId
        } else {
            plan[stelle]!.ankunft = plan[stelle]!.schritt.von
        }
    }
    return plan
}

/** Wer diese erzeugte Anfahrt mitfährt: wer laut eigenem Plan davor am Startort stand. */
export function mitfahrer(daten: Plandaten, lauf: Lauf, schritt: Schritt): string[] {
    const weg = anfahrt(daten, lauf, schritt)
    if (!weg) return []
    const dabei = lauf.personId ? [lauf.personId] : []
    dabei.push(...schritt.besatzung.map(platz => platz.personId))
    return dabei.filter(personId => personenplan(daten, personId)
        .some(eintrag => eintrag.schritt.id === schritt.id && eintrag.vonOrtId === weg.vonOrtId))
}

/** Wer und was an diesem Ort steht, nach Zeit sortiert — die Ortssicht. */
export function ortssicht(daten: Plandaten, ortId: string): Ortsbelegung[] {
    const belegungen: Ortsbelegung[] = []
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) {
            if (schritt.art !== 'aufenthalt' || schritt.ortId !== ortId) continue
            belegungen.push({
                lauf, schritt, von: ankunft(daten, lauf, schritt), bis: schritt.bis,
                personIds: lauf.personId
                    ? [lauf.personId, ...schritt.besatzung.map(platz => platz.personId)]
                    : schritt.besatzung.map(platz => platz.personId),
            })
        }
    }
    return nachZeit(belegungen)
}

/**
 * Wann eine Lage läuft und wer an ihr hängt. Die Lage selbst trägt weder Zeiten noch Teilnehmer
 * — sie kann sich damit nicht selbst widersprechen, und zwei Fahrzeuge an derselben Lage teilen
 * sich einen Eintrag statt ihn zu verdoppeln.
 */
export function lagensicht(daten: Plandaten, punkt: Programmpunkt): Lagensicht {
    const sicht: Lagensicht = {programmpunkt: punkt, ortId: '', von: '', bis: '', laeufe: [],
        personIds: []}
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) {
            if (schritt.programmpunktId !== punkt.id) continue
            if (!sicht.ortId) sicht.ortId = schritt.ortId
            const da = ankunft(daten, lauf, schritt)
            if (!sicht.von || (alsMinuten(da) ?? 0) < (alsMinuten(sicht.von) ?? 0)) {
                sicht.von = da
            }
            if (!sicht.bis || (alsMinuten(schritt.bis) ?? 0) > (alsMinuten(sicht.bis) ?? 0)) {
                sicht.bis = schritt.bis
            }
            if (!sicht.laeufe.includes(lauf)) sicht.laeufe.push(lauf)
            for (const personId of [lauf.personId, ...schritt.besatzung.map(p => p.personId)]) {
                if (personId && !sicht.personIds.includes(personId)) sicht.personIds.push(personId)
            }
        }
    }
    return sicht
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
    if (klasse && schritt.art === 'fahrt') {
        for (const platz of fahrer) {
            const wer = person(daten, platz.personId)
            if (wer && !darfFahren(daten, lauf.fahrzeugId, wer.id)) {
                befunde.push({
                    art: 'ohneErlaubnis', ...stelle, personId: wer.id,
                    werte: {wer: wer.name, klasse},
                })
            }
        }
    }

    const geschaetzt = fahrzeitSchaetzung(daten, lauf, schritt)
    const geplant = dauer(schritt.von, schritt.bis)
    if (schritt.art === 'fahrt' && geschaetzt !== null && geplant !== null
        && geplant < geschaetzt * KNAPP) {
        befunde.push({art: 'zuKnapp', ...stelle, werte: {geplant, geschaetzt}})
    }

    const weg = anfahrt(daten, lauf, schritt)
    if (weg && weg.minuten > 0 && geplant !== null && geplant <= weg.minuten) {
        befunde.push({art: 'fahrtFrisstAufenthalt', ...stelle,
            werte: {fahrzeit: weg.minuten, geplant}})
    }
    return befunde
}

/**
 * Geschätzte Fahrzeit zwischen zwei Orten: Luftlinie mal Minuten je Kilometer, auf fünf Minuten
 * gerundet und nie unter fünf. Ohne Koordinaten an einem der beiden Orte gibt es keine Schätzung
 * — die Luftlinie kennt ohnehin weder Spree noch Baustelle.
 */
export function schaetzung(daten: Plandaten, vonOrtId: string, nachOrtId: string,
                           mittel: Mittel): number | null {
    if (mittel === 'eigen' || vonOrtId === nachOrtId) return null
    const von = daten.punkte?.[vonOrtId]
    const nach = daten.punkte?.[nachOrtId]
    if (!von || !nach) return null
    return Math.max(5, Math.round(entfernungKm(von, nach) * MINUTEN_JE_KM[mittel] / 5) * 5)
}

/**
 * Die Schätzung, die zu diesem Schritt gehört: bei einer eingetragenen Fahrt die für sie selbst,
 * bei einem Aufenthalt die für seine erzeugte Anfahrt.
 */
export function fahrzeitSchaetzung(daten: Plandaten, lauf: Lauf, schritt: Schritt): number | null {
    if (schritt.art === 'fahrt') {
        return schaetzung(daten, vonOrt(lauf, schritt), schritt.ortId, mittelVon(lauf, schritt))
    }
    const weg = anfahrt(daten, lauf, schritt)
    return weg ? schaetzung(daten, weg.vonOrtId, weg.nachOrtId, weg.mittel) : null
}

/**
 * Zwei Schritte einer Kette, die sich zeitlich überlappen. Eine Kette ist eine Folge, und die
 * Oberfläche hält sie lückenlos — aber eine geänderte Zeit, ein anderer Browser oder eine von
 * Hand geladene Datei können sie brechen, und dann steht ein Fahrzeug an zwei Orten zugleich,
 * ohne dass eine der anderen Prüfungen anschlüge.
 */
function ueberschneidungBefunde(lauf: Lauf): Befund[] {
    const befunde: Befund[] = []
    for (let stelle = 1; stelle < lauf.schritte.length; stelle++) {
        const vorher = lauf.schritte[stelle - 1]!
        const jetzt = lauf.schritte[stelle]!
        if (!ueberschneidet(vorher.von, vorher.bis, jetzt.von, jetzt.bis)) continue
        befunde.push({art: 'ueberschneidung', laufId: lauf.id, schrittId: jetzt.id})
    }
    return befunde
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

/**
 * Dieselbe Person zur selben Zeit in zwei Ketten. Gemeldet wird je Schritt einmal und nicht je
 * Paar — zwei ganztägige Ketten ergäben sonst eine Wand aus derselben Meldung.
 */
function doppelBefunde(daten: Plandaten, personId: string, plan: Personenschritt[]): Befund[] {
    const betroffen = new Set<string>()
    for (let a = 0; a < plan.length; a++) {
        for (let b = a + 1; b < plan.length; b++) {
            const eins = plan[a]!, zwei = plan[b]!
            if (eins.lauf.id === zwei.lauf.id) continue
            if (!ueberschneidet(eins.schritt.von, eins.schritt.bis,
                                zwei.schritt.von, zwei.schritt.bis)) continue
            betroffen.add(zwei.schritt.id)
        }
    }
    return plan
        .filter(eintrag => betroffen.has(eintrag.schritt.id))
        .map(eintrag => ({
            art: 'zweiOrte' as const, personId,
            laufId: eintrag.lauf.id, schrittId: eintrag.schritt.id,
            werte: {wer: name(daten, personId)},
        }))
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

/**
 * Mehr Material verplant, als es gibt.
 *
 * Gezählt wird über die Zeit und nicht über einen Schritt: vier Puppen sind zweimal gleichzeitig
 * eingeplant acht. Geprüft wird an jedem Zeitpunkt, an dem sich etwas ändert — dazwischen kann
 * die Summe nicht steigen. Ohne erfassten Bestand wird nicht gezählt.
 */
function materialBefunde(daten: Plandaten): Befund[] {
    const befunde: Befund[] = []
    for (const stueck of daten.kataloge?.material ?? []) {
        if (!stueck.bestand) continue
        const belegungen = daten.planung.laeufe.flatMap(lauf => lauf.schritte.flatMap(schritt =>
            schritt.material
                .filter(posten => posten.materialId === stueck.id)
                .map(posten => ({
                    laufId: lauf.id, schrittId: schritt.id, anzahl: posten.anzahl,
                    von: alsMinuten(schritt.von) ?? 0, bis: alsMinuten(schritt.bis) ?? 0,
                }))))
        for (const beginn of belegungen.map(belegung => belegung.von)) {
            const gleichzeitig = belegungen.filter(
                belegung => belegung.von <= beginn && beginn < belegung.bis)
            const summe = gleichzeitig.reduce((zahl, belegung) => zahl + belegung.anzahl, 0)
            if (summe <= stueck.bestand) continue
            for (const belegung of gleichzeitig) {
                befunde.push({
                    art: 'zuVielMaterial', laufId: belegung.laufId, schrittId: belegung.schrittId,
                    werte: {was: stueck.name, verplant: summe, bestand: stueck.bestand},
                })
            }
        }
    }
    return befunde
}

/** Alle Prüfungen über den ganzen Plan. */
export function pruefen(daten: Plandaten): Befund[] {
    const befunde: Befund[] = []
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) befunde.push(...schrittBefunde(daten, lauf, schritt))
        befunde.push(...ueberschneidungBefunde(lauf))
    }
    for (const wer of daten.personen) {
        const plan = personenplan(daten, wer.id)
        befunde.push(...zustiegBefunde(daten, wer.id, plan))
        befunde.push(...doppelBefunde(daten, wer.id, plan))
        befunde.push(...ausserhalbBefunde(wer, plan))
    }
    befunde.push(...materialBefunde(daten))
    const benutzt = new Set(daten.planung.laeufe
        .flatMap(lauf => lauf.schritte.map(schritt => schritt.programmpunktId)))
    for (const punkt of daten.planung.programmpunkte) {
        if (!benutzt.has(punkt.id)) {
            befunde.push({art: 'lageLeer', programmpunktId: punkt.id, werte: {was: punkt.name}})
            continue
        }
        const orte = new Set(daten.planung.laeufe.flatMap(lauf => lauf.schritte
            .filter(schritt => schritt.programmpunktId === punkt.id)
            .map(schritt => schritt.ortId)))
        if (orte.size > 1) {
            befunde.push({art: 'lageZweiOrte', programmpunktId: punkt.id,
                werte: {was: punkt.name, anzahl: orte.size}})
        }
    }
    return befunde
}
