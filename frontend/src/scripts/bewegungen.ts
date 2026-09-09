/**
 * Das Bewegungsbild: welcher Ort wann von wem belegt ist, und wer zwischen welchen Orten
 * unterwegs ist.
 *
 * Jeder Ort ist ein waagerechtes Band, die Zeit läuft nach rechts. Ein Aufenthalt ist ein Balken
 * im Band, eine Fahrt eine Linie, die von einem Band ins andere zieht. Damit ist die Bewegung
 * selbst das Bild und nicht bloß eine Zeile in einer Tabelle — genau die Ansicht, die eine
 * Tabelle nie geben konnte.
 *
 * Gerechnet wird hier nur die Anordnung, nicht das Aussehen: Bänder, Reihen darin, Zeitfenster.
 * Dieselbe Anordnung zeichnet der Bildschirm und das PDF, und `tools/bewegungen_vergleichen`
 * hält die beiden Seiten aneinander.
 */
import type {Lauf, Schritt} from '../interfaces/Planung'
import type {Plandaten} from './ablauf'
import {vonOrt} from './ablauf'
import {alsMinuten, tagVon} from './zeit'

/** Ein Ort als Band. `reihen` sagt, wie viele Balken darin nebeneinander liegen müssen. */
export interface Band {
    ortId: string
    name: string
    reihen: number
}

/** Ein Aufenthalt: jemand steht von — bis in diesem Band. */
export interface Balken {
    laufId: string
    schrittId: string
    ortId: string
    reihe: number
    /** Minuten seit Mitternacht des Tages; über Mitternacht hinaus größer als 1440. */
    von: number
    bis: number
    name: string
    besatzung: string[]
    lage: string
}

/** Eine Fahrt: die Linie, die ein Band verlässt und in einem anderen ankommt. */
export interface Linie {
    laufId: string
    schrittId: string
    vonOrtId: string
    vonReihe: number
    nachOrtId: string
    nachReihe: number
    von: number
    bis: number
    mittel: Schritt['mittel']
    name: string
}

export interface Bewegungsbild {
    datum: string
    /** Das Zeitfenster, auf volle Stunden gelegt, damit die Achse runde Zahlen trägt. */
    von: number
    bis: number
    baender: Band[]
    balken: Balken[]
    linien: Linie[]
}

const STUNDE = 60

function minuteAmTag(zeitpunkt: string, datum: string): number {
    return (alsMinuten(zeitpunkt) ?? 0) - (alsMinuten(`${datum}T00:00`) ?? 0)
}

/** Die Tage, an denen überhaupt etwas geplant ist, in ihrer natürlichen Reihenfolge. */
export function bewegungstage(daten: Plandaten): string[] {
    const tage = new Set<string>()
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) {
            const tag = tagVon(schritt.von)
            if (tag) tage.add(tag)
        }
    }
    return [...tage].sort()
}

function name(daten: Plandaten, lauf: Lauf): string {
    if (lauf.fahrzeugId) {
        return daten.fahrzeuge.find(fahrzeug => fahrzeug.id === lauf.fahrzeugId)?.funkrufname ?? ''
    }
    return daten.planung.personen.find(person => person.id === lauf.personId)?.name ?? ''
}

function besatzung(daten: Plandaten, schritt: Schritt): string[] {
    return schritt.besatzung.map(platz =>
        daten.planung.personen.find(person => person.id === platz.personId)?.name ?? '')
}

/**
 * Die Reihe im Band: der erste Platz, der zu dieser Zeit frei ist. Zwei Fahrzeuge, die
 * nacheinander an demselben Ort stehen, teilen sich damit eine Reihe, und nur was wirklich
 * gleichzeitig dasteht, braucht Platz übereinander.
 */
function reiheSuchen(belegt: number[], von: number, bis: number): number {
    for (let reihe = 0; reihe < belegt.length; reihe++) {
        if (belegt[reihe]! <= von) {
            belegt[reihe] = bis
            return reihe
        }
    }
    belegt.push(bis)
    return belegt.length - 1
}

interface Aufenthalt {
    lauf: Lauf
    schritt: Schritt
    von: number
    bis: number
}

function aufenthalte(daten: Plandaten, datum: string): Aufenthalt[] {
    const gefunden: Aufenthalt[] = []
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) {
            if (schritt.art !== 'aufenthalt' || tagVon(schritt.von) !== datum) continue
            gefunden.push({lauf, schritt,
                           von: minuteAmTag(schritt.von, datum),
                           bis: minuteAmTag(schritt.bis, datum)})
        }
    }
    return gefunden.sort((a, b) => a.von - b.von)
}

/**
 * Das Bild eines Tages. Ein Ort bekommt ein Band, sobald jemand dort steht oder dorthin fährt;
 * Orte, an denen an diesem Tag nichts geschieht, tauchen nicht auf.
 */
export function bewegungsbild(daten: Plandaten, datum: string): Bewegungsbild {
    const stehend = aufenthalte(daten, datum)
    const fahrten = daten.planung.laeufe.flatMap(lauf => lauf.schritte
        .filter(schritt => schritt.art === 'fahrt' && tagVon(schritt.von) === datum)
        .map(schritt => ({lauf, schritt})))

    const beteiligt: string[] = []
    for (const ortId of [
        ...stehend.map(eintrag => eintrag.schritt.ortId),
        ...fahrten.flatMap(({lauf, schritt}) => [vonOrt(lauf, schritt), schritt.ortId]),
    ]) {
        if (ortId && !beteiligt.includes(ortId)) beteiligt.push(ortId)
    }
    const reihenfolge = daten.planung.orte
        .filter(ort => beteiligt.includes(ort.id))
        .map(ort => ort.id)

    const belegung = new Map<string, number[]>(reihenfolge.map(ortId => [ortId, []]))
    const reihen = new Map<string, number>()
    const balken: Balken[] = []
    for (const eintrag of stehend) {
        const belegt = belegung.get(eintrag.schritt.ortId)
        if (!belegt) continue
        const reihe = reiheSuchen(belegt, eintrag.von, eintrag.bis)
        reihen.set(eintrag.schritt.id, reihe)
        balken.push({
            laufId: eintrag.lauf.id, schrittId: eintrag.schritt.id,
            ortId: eintrag.schritt.ortId, reihe, von: eintrag.von, bis: eintrag.bis,
            name: name(daten, eintrag.lauf),
            besatzung: besatzung(daten, eintrag.schritt),
            lage: daten.planung.programmpunkte
                .find(punkt => punkt.id === eintrag.schritt.programmpunktId)?.name ?? '',
        })
    }

    const linien: Linie[] = fahrten.map(({lauf, schritt}) => {
        const stelle = lauf.schritte.indexOf(schritt)
        const abfahrt = lauf.schritte[stelle - 1]
        const ankunft = lauf.schritte[stelle + 1]
        return {
            laufId: lauf.id, schrittId: schritt.id,
            vonOrtId: vonOrt(lauf, schritt),
            vonReihe: abfahrt ? reihen.get(abfahrt.id) ?? 0 : 0,
            nachOrtId: schritt.ortId,
            nachReihe: ankunft ? reihen.get(ankunft.id) ?? 0 : 0,
            von: minuteAmTag(schritt.von, datum), bis: minuteAmTag(schritt.bis, datum),
            mittel: schritt.mittel, name: name(daten, lauf),
        }
    })

    const zeiten = [...balken, ...linien].flatMap(eintrag => [eintrag.von, eintrag.bis])
    const von = zeiten.length ? Math.floor(Math.min(...zeiten) / STUNDE) * STUNDE : 0
    const bis = zeiten.length ? Math.ceil(Math.max(...zeiten) / STUNDE) * STUNDE : STUNDE
    return {
        datum, von, bis: Math.max(bis, von + STUNDE),
        baender: reihenfolge.map(ortId => ({
            ortId,
            name: daten.planung.orte.find(ort => ort.id === ortId)?.name ?? '',
            reihen: Math.max(1, belegung.get(ortId)?.length ?? 1),
        })),
        balken, linien,
    }
}

/** Wo eine Kette zu einem Zeitpunkt ist: an einem Ort, oder zwischen zweien unterwegs. */
export interface Standort {
    laufId: string
    name: string
    art: 'fahrzeug' | 'person'
    /** Der Ort, an dem sie steht. Leer, solange sie unterwegs ist. */
    ortId: string
    unterwegs: Unterwegs | null
    personen: string[]
    lage: string
}

export interface Unterwegs {
    vonOrtId: string
    nachOrtId: string
    /** Wie weit die Strecke zurückgelegt ist, zwischen 0 und 1. */
    anteil: number
    mittel: Schritt['mittel']
}

/**
 * Der Stand zu einem Zeitpunkt — das, was am Ausführungstag zählt: wer steht wo, wer ist
 * unterwegs und wie weit. Wer zu dieser Zeit nichts geplant hat, taucht nicht auf.
 */
export function standorte(daten: Plandaten, zeitpunkt: string): Standort[] {
    const jetzt = alsMinuten(zeitpunkt)
    if (jetzt === null) return []
    const gefunden: Standort[] = []
    for (const lauf of daten.planung.laeufe) {
        const schritt = lauf.schritte.find(kandidat => {
            const von = alsMinuten(kandidat.von), bis = alsMinuten(kandidat.bis)
            return von !== null && bis !== null && von <= jetzt && jetzt < bis
        })
        if (!schritt) continue
        const von = alsMinuten(schritt.von) ?? 0
        const bis = alsMinuten(schritt.bis) ?? von + 1
        gefunden.push({
            laufId: lauf.id, name: name(daten, lauf),
            art: lauf.fahrzeugId ? 'fahrzeug' : 'person',
            ortId: schritt.art === 'fahrt' ? '' : schritt.ortId,
            unterwegs: schritt.art !== 'fahrt' ? null : {
                vonOrtId: vonOrt(lauf, schritt), nachOrtId: schritt.ortId,
                anteil: bis > von ? (jetzt - von) / (bis - von) : 0,
                mittel: schritt.mittel,
            },
            personen: lauf.personId
                ? [name(daten, lauf), ...besatzung(daten, schritt)]
                : besatzung(daten, schritt),
            lage: daten.planung.programmpunkte
                .find(punkt => punkt.id === schritt.programmpunktId)?.name ?? '',
        })
    }
    return gefunden
}

/** Was als Nächstes ansteht. */
export interface Ereignis {
    zeitpunkt: string
    art: 'abfahrt' | 'ankunft'
    name: string
    ortId: string
    lage: string
    /** Minuten von jetzt bis dahin. */
    in: number
}

/**
 * Die nächsten Ereignisse ab einem Zeitpunkt: jede Abfahrt und jede Ankunft, in der Reihenfolge,
 * in der sie eintreten. Am Ausführungstag ist das die eigentliche Frage — was kommt als
 * Nächstes, und wie lange noch.
 */
export function ereignisse(daten: Plandaten, zeitpunkt: string, anzahl = 8): Ereignis[] {
    const jetzt = alsMinuten(zeitpunkt)
    if (jetzt === null) return []
    const gefunden: Ereignis[] = []
    for (const lauf of daten.planung.laeufe) {
        for (const schritt of lauf.schritte) {
            const beginn = alsMinuten(schritt.von)
            if (beginn === null || beginn < jetzt) continue
            gefunden.push({
                zeitpunkt: schritt.von,
                art: schritt.art === 'fahrt' ? 'abfahrt' : 'ankunft',
                name: name(daten, lauf), ortId: schritt.ortId,
                lage: daten.planung.programmpunkte
                    .find(punkt => punkt.id === schritt.programmpunktId)?.name ?? '',
                in: beginn - jetzt,
            })
        }
    }
    return gefunden.sort((a, b) => a.in - b.in).slice(0, anzahl)
}
