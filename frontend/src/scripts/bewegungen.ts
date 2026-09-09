/**
 * Das Bewegungsbild: welcher Ort wann von wem belegt ist, und wer zwischen welchen Orten
 * unterwegs ist.
 *
 * Jeder Ort ist ein waagerechtes Band, die Zeit läuft nach rechts. Ein Aufenthalt ist ein Balken
 * im Band, eine Fahrt eine Linie, die von einem Band ins andere zieht. Damit ist die Bewegung
 * selbst das Bild und nicht bloß eine Zeile in einer Tabelle.
 *
 * Erzählt wird der Tag wahlweise je Fahrzeug oder je Person. Beides ist dieselbe Rechnung über
 * **Spuren** — eine Spur ist eine Folge von Schritten mit einem Namen. Im Fahrzeugbild ist das
 * eine Kette, im Personenbild der Plan einer Person, der ohnehin aus denselben Ketten entsteht.
 *
 * Gerechnet wird hier nur die Anordnung, nicht das Aussehen: Bänder, Reihen darin, Zeitfenster.
 * Dieselbe Anordnung zeichnet der Bildschirm und das PDF, und `tools/plan_vergleichen` hält die
 * beiden Seiten aneinander.
 */
import type {Lauf, Schritt} from '../interfaces/Planung'
import type {Plandaten} from './ablauf'
import {personenplan, vonOrt} from './ablauf'
import {alsMinuten, tagVon} from './zeit'

/** Wovon der Tag erzählt wird. */
export type Modus = 'fahrzeuge' | 'personen'

/** Ein Ort als Band. `reihen` sagt, wie viele Balken darin nebeneinander liegen müssen. */
export interface Band {
    ortId: string
    name: string
    reihen: number
}

/** Ein Aufenthalt: jemand steht von — bis in diesem Band. */
export interface Balken {
    spurId: string
    schrittId: string
    ortId: string
    reihe: number
    /** Minuten seit Mitternacht des Tages; über Mitternacht hinaus größer als 1440. */
    von: number
    bis: number
    name: string
    /**
     * Wer oder was noch dazugehört: im Fahrzeugbild die Besatzung, im Personenbild das
     * Fahrzeug, in dem die Person sitzt. Leer, wo jemand für sich steht.
     */
    begleitung: string[]
    lage: string
}

/** Eine Fahrt: die Linie, die ein Band verlässt und in einem anderen ankommt. */
export interface Linie {
    spurId: string
    schrittId: string
    vonOrtId: string
    vonReihe: number
    nachOrtId: string
    nachReihe: number
    von: number
    bis: number
    mittel: Schritt['mittel']
    name: string
    begleitung: string[]
}

export interface Bewegungsbild {
    datum: string
    modus: Modus
    /** Das Zeitfenster, auf volle Stunden gelegt, damit die Achse runde Zahlen trägt. */
    von: number
    bis: number
    baender: Band[]
    balken: Balken[]
    linien: Linie[]
}

/** Ein Schritt, wie ihn eine Spur sieht: mit dem Ort, an dem er anfängt, und seinem Umfeld. */
interface Spurschritt {
    schritt: Schritt
    vonOrtId: string
    begleitung: string[]
}

interface Spur {
    id: string
    name: string
    schritte: Spurschritt[]
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

function fahrzeugName(daten: Plandaten, fahrzeugId: string): string {
    return daten.fahrzeuge.find(fahrzeug => fahrzeug.id === fahrzeugId)?.funkrufname ?? ''
}

function personName(daten: Plandaten, personId: string): string {
    return daten.planung.personen.find(person => person.id === personId)?.name ?? ''
}

function laufName(daten: Plandaten, lauf: Lauf): string {
    return lauf.fahrzeugId
        ? fahrzeugName(daten, lauf.fahrzeugId)
        : personName(daten, lauf.personId)
}

function besatzung(daten: Plandaten, schritt: Schritt): string[] {
    return schritt.besatzung.map(platz => personName(daten, platz.personId))
}

/** Im Fahrzeugbild ist jede Kette eine Spur — die eines Fahrzeugs wie die einer Person. */
function fahrzeugspuren(daten: Plandaten): Spur[] {
    return daten.planung.laeufe.map(lauf => ({
        id: lauf.id, name: laufName(daten, lauf),
        schritte: lauf.schritte.map(schritt => ({
            schritt, vonOrtId: vonOrt(lauf, schritt), begleitung: besatzung(daten, schritt),
        })),
    }))
}

/**
 * Im Personenbild ist jede Person eine Spur. Ihr Plan wird nirgends gepflegt, sondern aus
 * denselben Ketten gerechnet — deshalb kann das Personenbild dem Fahrzeugbild nicht
 * widersprechen.
 */
function personenspuren(daten: Plandaten): Spur[] {
    return daten.planung.personen.map(person => ({
        id: person.id, name: person.name,
        schritte: personenplan(daten, person.id).map(eintrag => ({
            schritt: eintrag.schritt,
            vonOrtId: eintrag.vonOrtId,
            begleitung: eintrag.lauf.fahrzeugId
                ? [fahrzeugName(daten, eintrag.lauf.fahrzeugId)]
                : [],
        })),
    }))
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

interface Anwesenheit {
    spur: Spur
    eintrag: Spurschritt
    von: number
    bis: number
}

/**
 * Das Bild eines Tages. Ein Ort bekommt ein Band, sobald jemand dort steht oder dorthin fährt;
 * Orte, an denen an diesem Tag nichts geschieht, tauchen nicht auf.
 */
export function bewegungsbild(daten: Plandaten, datum: string,
                              modus: Modus = 'fahrzeuge'): Bewegungsbild {
    const spuren = modus === 'personen' ? personenspuren(daten) : fahrzeugspuren(daten)
    const amTag = (eintrag: Spurschritt) => tagVon(eintrag.schritt.von) === datum

    const stehend: Anwesenheit[] = []
    for (const spur of spuren) {
        for (const eintrag of spur.schritte) {
            if (eintrag.schritt.art !== 'aufenthalt' || !amTag(eintrag)) continue
            stehend.push({spur, eintrag,
                          von: minuteAmTag(eintrag.schritt.von, datum),
                          bis: minuteAmTag(eintrag.schritt.bis, datum)})
        }
    }
    stehend.sort((a, b) => a.von - b.von)

    const fahrten = spuren.flatMap(spur => spur.schritte
        .filter(eintrag => eintrag.schritt.art === 'fahrt' && amTag(eintrag))
        .map(eintrag => ({spur, eintrag})))

    const beteiligt = new Set<string>()
    for (const {eintrag} of stehend) beteiligt.add(eintrag.schritt.ortId)
    for (const {eintrag} of fahrten) {
        beteiligt.add(eintrag.vonOrtId)
        beteiligt.add(eintrag.schritt.ortId)
    }
    const reihenfolge = daten.planung.orte
        .filter(ort => ort.id && beteiligt.has(ort.id))
        .map(ort => ort.id)

    const belegung = new Map<string, number[]>(reihenfolge.map(ortId => [ortId, []]))
    const reihen = new Map<string, number>()
    const balken: Balken[] = []
    for (const anwesend of stehend) {
        const belegt = belegung.get(anwesend.eintrag.schritt.ortId)
        if (!belegt) continue
        const reihe = reiheSuchen(belegt, anwesend.von, anwesend.bis)
        reihen.set(`${anwesend.spur.id}|${anwesend.eintrag.schritt.id}`, reihe)
        balken.push({
            spurId: anwesend.spur.id, schrittId: anwesend.eintrag.schritt.id,
            ortId: anwesend.eintrag.schritt.ortId, reihe,
            von: anwesend.von, bis: anwesend.bis, name: anwesend.spur.name,
            begleitung: anwesend.eintrag.begleitung,
            lage: daten.planung.programmpunkte
                .find(punkt => punkt.id === anwesend.eintrag.schritt.programmpunktId)?.name ?? '',
        })
    }

    const linien: Linie[] = fahrten.map(({spur, eintrag}) => {
        const stelle = spur.schritte.indexOf(eintrag)
        const abfahrt = spur.schritte[stelle - 1]
        const ankunft = spur.schritte[stelle + 1]
        const reihe = (nachbar: Spurschritt | undefined) =>
            nachbar ? reihen.get(`${spur.id}|${nachbar.schritt.id}`) ?? 0 : 0
        return {
            spurId: spur.id, schrittId: eintrag.schritt.id,
            vonOrtId: eintrag.vonOrtId, vonReihe: reihe(abfahrt),
            nachOrtId: eintrag.schritt.ortId, nachReihe: reihe(ankunft),
            von: minuteAmTag(eintrag.schritt.von, datum),
            bis: minuteAmTag(eintrag.schritt.bis, datum),
            mittel: eintrag.schritt.mittel, name: spur.name,
            begleitung: eintrag.begleitung,
        }
    })

    const zeiten = [...balken, ...linien].flatMap(eintrag => [eintrag.von, eintrag.bis])
    const von = zeiten.length ? Math.floor(Math.min(...zeiten) / STUNDE) * STUNDE : 0
    const bis = zeiten.length ? Math.ceil(Math.max(...zeiten) / STUNDE) * STUNDE : STUNDE
    return {
        datum, modus, von, bis: Math.max(bis, von + STUNDE),
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
            laufId: lauf.id, name: laufName(daten, lauf),
            art: lauf.fahrzeugId ? 'fahrzeug' : 'person',
            ortId: schritt.art === 'fahrt' ? '' : schritt.ortId,
            unterwegs: schritt.art !== 'fahrt' ? null : {
                vonOrtId: vonOrt(lauf, schritt), nachOrtId: schritt.ortId,
                anteil: bis > von ? (jetzt - von) / (bis - von) : 0,
                mittel: schritt.mittel,
            },
            personen: lauf.personId
                ? [laufName(daten, lauf), ...besatzung(daten, schritt)]
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
                name: laufName(daten, lauf), ortId: schritt.ortId,
                lage: daten.planung.programmpunkte
                    .find(punkt => punkt.id === schritt.programmpunktId)?.name ?? '',
                in: beginn - jetzt,
            })
        }
    }
    return gefunden.sort((a, b) => a.in - b.in).slice(0, anzahl)
}
