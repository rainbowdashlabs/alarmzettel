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
import type {Anfahrt, Plandaten} from './ablauf'
import {anfahrt, lagenName, personenplan, vonOrt} from './ablauf'
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
    material: string[]
    notiz: string
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
    material: string[]
    notiz: string
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
    /** Die erzeugte Anfahrt, sofern diese Spur sie mitfährt. */
    anfahrt: Anfahrt | null
    /** Wann diese Spur an ihrem Ort steht — nach der Anfahrt, sonst mit dem Beginn. */
    ankunft: string
    begleitung: string[]
}

/** Die Menge steht davor, wo es mehr als eines ist — sonst nur der Name. */
function materialnamen(daten: Plandaten, schritt: Schritt): string[] {
    return schritt.material
        .map(posten => {
            const name = daten.kataloge?.material
                ?.find(stueck => stueck.id === posten.materialId)?.name ?? ''
            return name && posten.anzahl > 1 ? `${posten.anzahl} × ${name}` : name
        })
        .filter(Boolean)
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
    return daten.personen.find(person => person.id === personId)?.name ?? ''
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
        schritte: lauf.schritte.map(schritt => {
            const weg = anfahrt(daten, lauf, schritt)
            return {
                schritt, vonOrtId: vonOrt(lauf, schritt), anfahrt: weg,
                ankunft: weg?.bis ?? schritt.von, begleitung: besatzung(daten, schritt),
            }
        }),
    }))
}

/**
 * Im Personenbild ist jede Person eine Spur. Ihr Plan wird nirgends gepflegt, sondern aus
 * denselben Ketten gerechnet — deshalb kann das Personenbild dem Fahrzeugbild nicht
 * widersprechen.
 */
function personenspuren(daten: Plandaten): Spur[] {
    return daten.personen.map(person => ({
        id: person.id, name: person.name,
        schritte: personenplan(daten, person.id).map(eintrag => {
            const weg = anfahrt(daten, eintrag.lauf, eintrag.schritt)
            const faehrtMit = weg !== null && eintrag.vonOrtId === weg.vonOrtId
            return {
                schritt: eintrag.schritt,
                vonOrtId: eintrag.vonOrtId,
                anfahrt: faehrtMit ? weg : null,
                ankunft: eintrag.ankunft,
                begleitung: eintrag.lauf.fahrzeugId
                    ? [fahrzeugName(daten, eintrag.lauf.fahrzeugId)]
                    : [],
            }
        }),
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
 *
 * Gefahren wird auf zweierlei Weise: als eingetragene Fahrt und als die Anfahrt, die zwischen
 * zwei Aufenthalten von selbst entsteht. Für das Bild ist beides dieselbe Linie — die
 * eingetragene endet im nächsten Schritt, die erzeugte in ihrem eigenen, denn sie gehört zu dem
 * Aufenthalt, zu dem sie führt.
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
                          von: minuteAmTag(eintrag.ankunft, datum),
                          bis: minuteAmTag(eintrag.schritt.bis, datum)})
        }
    }
    stehend.sort((a, b) => a.von - b.von)

    const fahrten = spuren.flatMap(spur => spur.schritte
        .filter(eintrag =>
            amTag(eintrag) && (eintrag.schritt.art === 'fahrt' || eintrag.anfahrt !== null))
        .map(eintrag => ({spur, eintrag})))

    const beteiligt = new Set<string>()
    for (const {eintrag} of stehend) beteiligt.add(eintrag.schritt.ortId)
    for (const {eintrag} of fahrten) {
        beteiligt.add(eintrag.anfahrt?.vonOrtId ?? eintrag.vonOrtId)
        beteiligt.add(eintrag.schritt.ortId)
    }
    const reihenfolge = daten.orte
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
            lage: lagenName(daten, anwesend.eintrag.schritt.programmpunktId),
            material: materialnamen(daten, anwesend.eintrag.schritt),
            notiz: anwesend.eintrag.schritt.notiz,
        })
    }

    const linien: Linie[] = fahrten.map(({spur, eintrag}) => {
        const stelle = spur.schritte.indexOf(eintrag)
        const abfahrt = spur.schritte[stelle - 1]
        const ankunft = eintrag.anfahrt ? eintrag : spur.schritte[stelle + 1]
        const reihe = (nachbar: Spurschritt | undefined) =>
            nachbar ? reihen.get(`${spur.id}|${nachbar.schritt.id}`) ?? 0 : 0
        return {
            spurId: spur.id, schrittId: eintrag.schritt.id,
            vonOrtId: eintrag.anfahrt?.vonOrtId ?? eintrag.vonOrtId, vonReihe: reihe(abfahrt),
            nachOrtId: eintrag.schritt.ortId, nachReihe: reihe(ankunft),
            von: minuteAmTag(eintrag.anfahrt?.von ?? eintrag.schritt.von, datum),
            bis: minuteAmTag(eintrag.anfahrt?.bis ?? eintrag.schritt.bis, datum),
            mittel: eintrag.anfahrt?.mittel ?? eintrag.schritt.mittel, name: spur.name,
            begleitung: eintrag.begleitung,
            material: materialnamen(daten, eintrag.schritt),
            notiz: eintrag.schritt.notiz,
        }
    })

    const zeiten = [...balken, ...linien].flatMap(eintrag => [eintrag.von, eintrag.bis])
    const von = zeiten.length ? Math.floor(Math.min(...zeiten) / STUNDE) * STUNDE : 0
    const bis = zeiten.length ? Math.ceil(Math.max(...zeiten) / STUNDE) * STUNDE : STUNDE
    return {
        datum, modus, von, bis: Math.max(bis, von + STUNDE),
        baender: reihenfolge.map(ortId => ({
            ortId,
            name: daten.orte.find(ort => ort.id === ortId)?.name ?? '',
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
 * Ob diese Kette zu diesem Zeitpunkt fährt: auf einer eingetragenen Fahrt, oder auf der Anfahrt,
 * die einem Aufenthalt vorausgeht und mit ihm beginnt.
 */
function unterwegsIn(daten: Plandaten, lauf: Lauf, schritt: Schritt,
                     jetzt: number): Unterwegs | null {
    const anteilig = (von: number, bis: number) => bis > von ? (jetzt - von) / (bis - von) : 0
    if (schritt.art === 'fahrt') {
        const von = alsMinuten(schritt.von) ?? 0
        return {
            vonOrtId: vonOrt(lauf, schritt), nachOrtId: schritt.ortId,
            anteil: anteilig(von, alsMinuten(schritt.bis) ?? von + 1), mittel: schritt.mittel,
        }
    }
    const weg = anfahrt(daten, lauf, schritt)
    if (!weg) return null
    const von = alsMinuten(weg.von) ?? 0
    const bis = alsMinuten(weg.bis) ?? von
    if (jetzt >= bis) return null
    return {
        vonOrtId: weg.vonOrtId, nachOrtId: weg.nachOrtId,
        anteil: anteilig(von, bis), mittel: weg.mittel,
    }
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
        const fahrend = unterwegsIn(daten, lauf, schritt, jetzt)
        gefunden.push({
            laufId: lauf.id, name: laufName(daten, lauf),
            art: lauf.fahrzeugId ? 'fahrzeug' : 'person',
            ortId: fahrend ? '' : schritt.ortId,
            unterwegs: fahrend,
            personen: lauf.personId
                ? [laufName(daten, lauf), ...besatzung(daten, schritt)]
                : besatzung(daten, schritt),
            lage: lagenName(daten, schritt.programmpunktId),
        })
    }
    return gefunden
}

/** Wo ein Stück Material zu einem Zeitpunkt liegt. */
export interface Materialstand {
    materialId: string
    name: string
    anzahl: number
    /** Der Ort, an dem es liegt. Leer, solange es unterwegs ist. */
    ortId: string
    unterwegs: Unterwegs | null
    /** Womit es unterwegs ist oder wer es dabeihat. */
    traeger: string
}

/**
 * Wo das Material gerade ist. Es hängt an den Schritten wie die Besatzung, also sagt der Plan es
 * von selbst — und wenn es fährt, sagt er auch, womit und wohin.
 */
export function materialstand(daten: Plandaten, zeitpunkt: string): Materialstand[] {
    const jetzt = alsMinuten(zeitpunkt)
    if (jetzt === null) return []
    const gefunden: Materialstand[] = []
    for (const stueck of daten.kataloge?.material ?? []) {
        for (const lauf of daten.planung.laeufe) {
            const schritt = lauf.schritte.find(kandidat =>
                kandidat.material.some(posten => posten.materialId === stueck.id) &&
                (alsMinuten(kandidat.von) ?? 0) <= jetzt && jetzt < (alsMinuten(kandidat.bis) ?? 0))
            if (!schritt) continue
            const posten = schritt.material.find(eintrag => eintrag.materialId === stueck.id)
            const fahrend = unterwegsIn(daten, lauf, schritt, jetzt)
            gefunden.push({
                materialId: stueck.id, name: stueck.name, anzahl: posten?.anzahl ?? 1,
                ortId: fahrend ? '' : schritt.ortId,
                unterwegs: fahrend,
                traeger: laufName(daten, lauf),
            })
            break
        }
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
            const weg = anfahrt(daten, lauf, schritt)
            const punkte: [string, Ereignis['art'], string][] = weg
                ? [[weg.von, 'abfahrt', weg.vonOrtId], [weg.bis, 'ankunft', weg.nachOrtId]]
                : [[schritt.von, schritt.art === 'fahrt' ? 'abfahrt' : 'ankunft', schritt.ortId]]
            for (const [zeit, art, ortId] of punkte) {
                const wann = alsMinuten(zeit)
                if (wann === null || wann < jetzt) continue
                gefunden.push({
                    zeitpunkt: zeit, art,
                    name: laufName(daten, lauf), ortId,
                    lage: lagenName(daten, schritt.programmpunktId),
                    in: wann - jetzt,
                })
            }
        }
    }
    return gefunden.sort((a, b) => a.in - b.in).slice(0, anzahl)
}
