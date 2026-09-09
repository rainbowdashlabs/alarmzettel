/**
 * Der Ablaufplan in der Arbeitsmappe: anlegen, entfernen, nachschlagen und die Ketten
 * fortschreiben.
 *
 * Gerechnet wird hier nichts. Personenplan, Ortssicht und die Prüfungen stehen in
 * `scripts/ablauf`, das nichts von einem Store weiß und deshalb auch außerhalb eines Browsers
 * geprüft werden kann.
 */
import {reactive} from 'vue'
import {arbeitsmappe} from './arbeitsmappe'
import {naechste, leereAdresse} from '../interfaces/Alarm'
import {zuPunkt} from '../api/adressen'
import {darfFahren as darfFahrenLaut, MINUTEN_JE_KM} from '../scripts/ablauf'
import {entfernungKm} from '../scripts/polar'
import type {Plandaten} from '../scripts/ablauf'
import type {Punkt} from '../scripts/polar'
import {tagVon, verschieben} from '../scripts/zeit'
import {DIENSTSTELLE} from '../interfaces/Planung'
import type {
    Besatzung, Lauf, Materialposten, Mittel, Ort, Person, Programmpunkt, Schritt, Tag,
    Verfuegbarkeit,
} from '../interfaces/Planung'

/**
 * Die Koordinaten der Orte, soweit der Adressdienst sie kennt. Sie kommen über das Netz, die
 * Prüfungen rechnen aber ohne Warten — deshalb liegen sie hier und werden einmal geladen.
 */
export const ortsPunkte = reactive<Record<string, Punkt>>({})

/**
 * Die Dienststelle zuerst, dann die angelegten. Sie ist kein Eintrag, den jemand anlegt, sondern
 * einer, den es gibt, solange die Wache eine Adresse hat — und deshalb auch keiner, den man
 * löschen kann.
 */
export function alleOrte(): Ort[] {
    return [
        {id: DIENSTSTELLE, sortierung: -1,
         name: arbeitsmappe.kataloge.wacheName || 'Dienststelle',
         adresse: arbeitsmappe.kataloge.wache},
        ...arbeitsmappe.kataloge.orte,
    ]
}

export async function punkteLaden() {
    for (const ort of alleOrte()) {
        const punkt = await zuPunkt(ort.adresse)
        if (punkt) ortsPunkte[ort.id] = punkt
        else delete ortsPunkte[ort.id]
    }
}

/** Alles, was die Ableitung braucht, aus der laufenden Arbeitsmappe. */
export function plandaten(): Plandaten {
    return {
        planung: arbeitsmappe.planung,
        fahrzeuge: arbeitsmappe.kataloge.fahrzeuge,
        orte: alleOrte(),
        personen: arbeitsmappe.kataloge.personen,
        kataloge: {material: arbeitsmappe.kataloge.material},
        punkte: ortsPunkte,
    }
}

export function planung() {
    return arbeitsmappe.planung
}

export function planungUmschalten(an: boolean) {
    arbeitsmappe.planung.aktiv = an
}

export function tagAnlegen(): Tag {
    const tag: Tag = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.kataloge.tage),
        datum: new Date().toISOString().slice(0, 10), name: '',
    }
    arbeitsmappe.kataloge.tage.push(tag)
    return tag
}

export function ortAnlegen(): Ort {
    const ort: Ort = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.kataloge.orte),
        name: '', adresse: leereAdresse(),
    }
    arbeitsmappe.kataloge.orte.push(ort)
    return ort
}

export function personAnlegen(): Person {
    const person: Person = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.kataloge.personen),
        name: '', rollen: [], fahrerlaubnis: [], anzahl: 1, verfuegbar: [],
    }
    arbeitsmappe.kataloge.personen.push(person)
    return person
}

/**
 * Ein Fenster, in dem jemand da ist. Wer keines hat, ist immer da — deshalb legt das erste
 * Fenster den ganzen ersten Tag an und wird von dort aus zurechtgezogen.
 */
export function verfuegbarkeitAnlegen(person: Person): Verfuegbarkeit {
    const tag = arbeitsmappe.kataloge.tage[0]?.datum ?? new Date().toISOString().slice(0, 10)
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

export function laufAnlegen(fuer: {fahrzeugId?: string, personId?: string}): Lauf {
    const lauf: Lauf = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.planung.laeufe),
        fahrzeugId: fuer.fahrzeugId ?? '', personId: fuer.personId ?? '', schritte: [],
    }
    arbeitsmappe.planung.laeufe.push(lauf)
    return lauf
}

export function laufVon(fuer: {fahrzeugId?: string, personId?: string}): Lauf | undefined {
    return arbeitsmappe.planung.laeufe.find(lauf =>
        (fuer.fahrzeugId ? lauf.fahrzeugId === fuer.fahrzeugId : !lauf.fahrzeugId) &&
        (fuer.personId ? lauf.personId === fuer.personId : !lauf.personId))
}

export function letzterSchritt(lauf: Lauf): Schritt | undefined {
    return lauf.schritte[lauf.schritte.length - 1]
}

/**
 * Hängt einen Schritt an. Er fängt an, wo der vorige aufhörte — Zeit, Ort und Besatzung kommen
 * von dort. Genau deshalb ist ein Sprung von A nach B ohne Weg dazwischen nicht darstellbar und
 * muss nicht geprüft werden.
 */
export function schrittAnhaengen(lauf: Lauf, art: Schritt['art'], minuten = 30): Schritt {
    const vorher = letzterSchritt(lauf)
    const beginn = vorher?.bis ?? standardBeginn()
    const schritt: Schritt = {
        id: crypto.randomUUID(), sortierung: naechste(lauf.schritte),
        art, mittel: lauf.fahrzeugId ? 'fahrzeug' : 'fuss',
        von: beginn, bis: verschieben(beginn, minuten),
        ortId: vorher?.ortId ?? alleOrte()[0]?.id ?? '',
        programmpunktId: '', aufgebot: true, notiz: '',
        besatzung: (vorher?.besatzung ?? []).map(sitzt => ({
            ...sitzt, id: crypto.randomUUID(),
        })),
        material: (vorher?.material ?? []).map(stueck => ({
            ...stueck, id: crypto.randomUUID(),
        })),
    }
    lauf.schritte.push(schritt)
    return schritt
}

function standardBeginn(): string {
    const tag = arbeitsmappe.kataloge.tage[0]?.datum ?? new Date().toISOString().slice(0, 10)
    return `${tag}T08:00`
}

/** Die folgenden Schritte mitziehen, damit die Kette lückenlos bleibt. */
export function nachziehen(lauf: Lauf, ab: Schritt) {
    let vorher = ab
    for (const schritt of lauf.schritte.slice(lauf.schritte.indexOf(ab) + 1)) {
        const laenge = (Date.parse(`${schritt.bis}:00Z`) - Date.parse(`${schritt.von}:00Z`)) / 60000
        schritt.von = vorher.bis
        schritt.bis = verschieben(schritt.von, Number.isFinite(laenge) ? laenge : 30)
        vorher = schritt
    }
}

export function besatzungHinzufuegen(schritt: Schritt, personId: string): Besatzung | undefined {
    if (schritt.besatzung.some(sitzt => sitzt.personId === personId)) return undefined
    const sitzt: Besatzung = {
        id: crypto.randomUUID(), sortierung: naechste(schritt.besatzung),
        personId, faehrt: false,
    }
    schritt.besatzung.push(sitzt)
    return sitzt
}

/**
 * Es fährt immer höchstens einer; wer das Lenkrad nimmt, nimmt es dem anderen ab. Ans Lenkrad
 * kommt nur, wer die Klasse des Fahrzeugs hat — abgeben darf dagegen jeder, sonst bliebe ein
 * Fahrer aus einer älteren Fassung für immer stehen.
 */
export function darfFahren(fahrzeugId: string, personId: string): boolean {
    return darfFahrenLaut(plandaten(), fahrzeugId, personId)
}

export function fahrerSetzen(lauf: Lauf, schritt: Schritt, personId: string) {
    const gewaehlt = schritt.besatzung.find(sitzt => sitzt.personId === personId)
    if (!gewaehlt) return
    if (!gewaehlt.faehrt && !darfFahren(lauf.fahrzeugId, personId)) return
    const vorher = gewaehlt.faehrt
    for (const sitzt of schritt.besatzung) sitzt.faehrt = false
    gewaehlt.faehrt = !vorher
}

/**
 * Material an einen Schritt hängen. Ein Name, den der Katalog noch nicht kennt, kommt dort dazu
 * — so wie ein neu geschriebenes Stichwort oder ein neuer Funkrufname.
 */
export function materialSichern(name: string): string {
    const sauber = name.trim()
    if (!sauber) return ''
    const vorhanden = arbeitsmappe.kataloge.material
        .find(stueck => stueck.name.trim().toLowerCase() === sauber.toLowerCase())
    if (vorhanden) return vorhanden.id
    const stueck = {id: crypto.randomUUID(), name: sauber, bestand: 0}
    arbeitsmappe.kataloge.material.push(stueck)
    return stueck.id
}

export function materialHinzufuegen(schritt: Schritt, materialId: string): Materialposten | undefined {
    if (!materialId || schritt.material.some(stueck => stueck.materialId === materialId)) {
        return undefined
    }
    const posten: Materialposten = {
        id: crypto.randomUUID(), sortierung: naechste(schritt.material), materialId, anzahl: 1,
    }
    schritt.material.push(posten)
    return posten
}

export function materialName(materialId: string): string {
    return arbeitsmappe.kataloge.material.find(stueck => stueck.id === materialId)?.name ?? ''
}

export function programmpunktAnlegen(ortId: string): Programmpunkt {
    const punkt: Programmpunkt = {
        id: crypto.randomUUID(), sortierung: naechste(arbeitsmappe.planung.programmpunkte),
        name: '', ortId, alarmId: '',
    }
    arbeitsmappe.planung.programmpunkte.push(punkt)
    return punkt
}

export function programmpunkt(id: string): Programmpunkt | undefined {
    return arbeitsmappe.planung.programmpunkte.find(punkt => punkt.id === id)
}

/**
 * Geschätzte Fahrzeit zwischen zwei Orten: Luftlinie mal Minuten je Kilometer. Nur ein
 * Vorschlag — die Luftlinie kennt weder Spree noch Baustelle. Ohne Adresse an einem der beiden
 * Orte gibt es keine Schätzung.
 */
export async function fahrzeitSchaetzen(vonOrtId: string, nachOrtId: string,
                                        mittel: Mittel): Promise<number | null> {
    const orte = alleOrte()
    const von = orte.find(ort => ort.id === vonOrtId)
    const nach = orte.find(ort => ort.id === nachOrtId)
    if (!von || !nach || von.id === nach.id) return null
    const [a, b] = await Promise.all([zuPunkt(von.adresse), zuPunkt(nach.adresse)])
    if (!a || !b) return null
    return Math.max(5, Math.round(entfernungKm(a, b) * MINUTEN_JE_KM[mittel] / 5) * 5)
}

/** Geht der Plan über mehr als einen Tag, reicht die Uhrzeit auf dem Schirm nicht mehr. */
export function mehrereTage(): boolean {
    const tage = new Set(arbeitsmappe.planung.laeufe
        .flatMap(lauf => lauf.schritte.map(schritt => tagVon(schritt.von))))
    tage.delete('')
    return tage.size > 1
}

export function ortName(ortId: string): string {
    return alleOrte().find(ort => ort.id === ortId)?.name ?? ''
}

export function personName(personId: string): string {
    return arbeitsmappe.kataloge.personen.find(person => person.id === personId)?.name ?? ''
}

/** Wie viele Köpfe an Bord dürfen. Leer heißt: unbekannt, dann wird nicht gezählt. */
export function plaetze(fahrzeugId: string): number | null {
    const roh = arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === fahrzeugId)?.plaetze?.trim()
    return roh && /^\d+$/.test(roh) ? Number(roh) : null
}
