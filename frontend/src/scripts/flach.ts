import type {Arbeitsmappe} from '../interfaces/Alarm'
import type {Planung} from '../interfaces/Planung'

/**
 * The working set as a flat map of path to value — the same shape the server merges on, so the
 * two sides talk about the same paths. Mirrors `backend/src/data/dokument.py`; the two are
 * checked against each other by a round-trip test on either side.
 *
 * The separator is the unit separator, because catalogue entries are part of the path and
 * contain both dots and slashes: "Allergie / Kontakt mit giftigen Tieren" is one Stichwort.
 */
export const TRENNER = '\u001f'

export type Flachbild = Record<string, unknown>

function pfad(...teile: string[]): string {
    return teile.join(TRENNER)
}

const ADRESSFELDER = ['strasse', 'hnr', 'objekt', 'plz', 'ort'] as const
const ALARM_UNTEROBJEKTE = ['id', 'sortierung', 'anfahrtsadresse', 'einsatzadresse', 'karte',
    'hinweise', 'einsatzmittel']

function adresse(basis: string, werte: Flachbild, quelle: Record<string, unknown> = {}) {
    for (const feld of ADRESSFELDER) werte[pfad(basis, feld)] = quelle[feld] ?? ''
}

const PLANUNGSLISTEN = ['rollen', 'fahrerlaubnisse'] as const

/**
 * Jede Liste des Plans mit den Feldern, die als Pfad je Eintrag geschrieben werden. Was darunter
 * hängt — Adresse, Verfügbarkeit, Schritte, Besatzung — steht in `planungsfelder`. Spiegelt
 * `PLANUNGSEINTRAEGE` in `backend/src/data/dokument.py`.
 */
const PLANUNGSEINTRAEGE = {
    tage: ['datum', 'name'],
    orte: ['name'],
    personen: ['name', 'anzahl'],
    programmpunkte: ['name', 'ortId', 'alarmId'],
    laeufe: ['fahrzeugId', 'personId'],
} as const

const SCHRITTFELDER = ['art', 'mittel', 'von', 'bis', 'ortId', 'programmpunktId'] as const

type Eintragsdaten = Record<string, unknown> & { id: string, sortierung?: number }

function eintragsfelder(basis: string, werte: Flachbild, eintrag: Eintragsdaten,
                        felder: readonly string[], stelle: number) {
    werte[pfad(basis, 'sortierung')] = eintrag.sortierung ?? stelle
    for (const feld of felder) werte[pfad(basis, feld)] = eintrag[feld] ?? ''
}

/**
 * Den Plan flach machen. Die Ketten sind das Tiefste im Dokument — Lauf, Schritt, Besatzung — und
 * jede Ebene trägt ihre eigene id, damit zwei Leute an verschiedenen Schritten desselben Laufs
 * arbeiten können, ohne sich zu überschreiben.
 */
function planungsfelder(werte: Flachbild, planung: Planung) {
    werte[pfad('planung', 'aktiv')] = planung.aktiv ?? false
    for (const liste of PLANUNGSLISTEN) {
        for (const wert of planung[liste] ?? []) werte[pfad('planung', liste, wert)] = true
    }

    for (const [liste, felder] of Object.entries(PLANUNGSEINTRAEGE)) {
        const eintraege = (planung[liste as keyof Planung] ?? []) as unknown as Eintragsdaten[]
        eintraege.forEach((eintrag, stelle) => {
            const basis = pfad('planung', liste, eintrag.id)
            eintragsfelder(basis, werte, eintrag, felder, stelle)

            if (liste === 'orte') {
                adresse(pfad(basis, 'adresse'), werte, eintrag.adresse as never)
            } else if (liste === 'personen') {
                for (const satz of ['rollen', 'fahrerlaubnis'] as const) {
                    for (const wert of (eintrag[satz] ?? []) as string[]) {
                        werte[pfad(basis, satz, wert)] = true
                    }
                }
                ;((eintrag.verfuegbar ?? []) as Eintragsdaten[]).forEach((fenster, platz) => {
                    eintragsfelder(pfad(basis, 'verfuegbar', fenster.id), werte, fenster,
                                   ['von', 'bis'], platz)
                })
            } else if (liste === 'laeufe') {
                ;((eintrag.schritte ?? []) as Eintragsdaten[]).forEach((schritt, platz) => {
                    const sbasis = pfad(basis, 'schritte', schritt.id)
                    eintragsfelder(sbasis, werte, schritt, SCHRITTFELDER, platz)
                    ;((schritt.besatzung ?? []) as Eintragsdaten[]).forEach((sitzt, rang) => {
                        eintragsfelder(pfad(sbasis, 'besatzung', sitzt.id), werte, sitzt,
                                       ['personId', 'faehrt'], rang)
                    })
                })
            }
        })
    }
}

export function flach(mappe: Arbeitsmappe): Flachbild {
    const werte: Flachbild = {}

    mappe.alarme.forEach((alarm, reihe) => {
        const basis = pfad('alarme', alarm.id)
        werte[pfad(basis, 'sortierung')] = alarm.sortierung ?? reihe

        for (const [feld, wert] of Object.entries(alarm)) {
            if (!ALARM_UNTEROBJEKTE.includes(feld)) werte[pfad(basis, feld)] = wert
        }
        adresse(pfad(basis, 'anfahrtsadresse'), werte, alarm.anfahrtsadresse as never)
        adresse(pfad(basis, 'einsatzadresse'), werte, alarm.einsatzadresse as never)
        for (const [feld, wert] of Object.entries(alarm.karte ?? {})) {
            werte[pfad(basis, 'karte', feld)] = wert
        }

        alarm.hinweise.forEach((hinweis, stelle) => {
            const hbasis = pfad(basis, 'hinweise', hinweis.id)
            werte[pfad(hbasis, 'sortierung')] = hinweis.sortierung ?? stelle
            for (const [feld, wert] of Object.entries(hinweis)) {
                if (feld !== 'id' && feld !== 'sortierung') werte[pfad(hbasis, feld)] = wert
            }
        })

        alarm.einsatzmittel.forEach((gruppe, stelle) => {
            const gbasis = pfad(basis, 'einsatzmittel', gruppe.id)
            werte[pfad(gbasis, 'sortierung')] = gruppe.sortierung ?? stelle
            werte[pfad(gbasis, 'gruppe')] = gruppe.gruppe ?? ''
            gruppe.fahrzeuge.forEach((fahrzeug, platz) => {
                const fbasis = pfad(gbasis, 'fahrzeuge', fahrzeug.id)
                werte[pfad(fbasis, 'sortierung')] = fahrzeug.sortierung ?? platz
                for (const [feld, wert] of Object.entries(fahrzeug)) {
                    if (feld !== 'id' && feld !== 'sortierung') werte[pfad(fbasis, feld)] = wert
                }
            })
        })
    })

    werte[pfad('kataloge', 'arbeitsgruppe')] = mappe.kataloge.arbeitsgruppe ?? ''
    adresse(pfad('kataloge', 'wache'), werte, mappe.kataloge.wache as never)
    // Status and Trupp are words and nothing else, so the word is its own key. Stichwörter and
    // vehicles are pointed at by the Alarme, so they are keyed by an id that a rename survives.
    for (const liste of ['status', 'trupp'] as const) {
        for (const wert of mappe.kataloge[liste]) werte[pfad('kataloge', liste, wert)] = true
    }
    for (const eintrag of mappe.kataloge.stichwoerter) {
        werte[pfad('kataloge', 'stichwoerter', eintrag.id, 'text')] = eintrag.text ?? ''
    }
    for (const vorlage of mappe.kataloge.fahrzeuge) {
        const vbasis = pfad('kataloge', 'fahrzeuge', vorlage.id)
        for (const feld of ['funkrufname', 'staerke', 'ezp', 'status'] as const) {
            werte[pfad(vbasis, feld)] = vorlage[feld] ?? ''
        }
    }
    if (mappe.planung) planungsfelder(werte, mappe.planung)
    return werte
}

type Sortierbar = { id: string, sortierung?: number }

function geordnet<T extends Sortierbar>(eintraege: Record<string, T>): T[] {
    return Object.values(eintraege).sort(
        (a, b) => (a.sortierung ?? 0) - (b.sortierung ?? 0) || a.id.localeCompare(b.id))
}

export function rund(werte: Flachbild): unknown {
    const alarme: Record<string, Record<string, never>> = {}
    const kataloge: Record<string, unknown> = {
        stichwoerter: {} as Record<string, Record<string, unknown>>,
        status: [] as string[], trupp: [] as string[],
        fahrzeuge: {} as Record<string, Record<string, unknown>>, arbeitsgruppe: '',
        wache: {} as Record<string, unknown>,
    }

    for (const [schluessel, wert] of Object.entries(werte)) {
        const teile = schluessel.split(TRENNER)
        if (teile[0] === 'kataloge' && teile.length === 2) {
            kataloge[teile[1]!] = wert
            continue
        }
        if (teile[0] === 'kataloge' && teile.length >= 3) {
            const liste = teile[1]!
            if (liste === 'wache' && teile.length === 3) {
                (kataloge['wache'] as Record<string, unknown>)[teile[2]!] = wert
            } else if (liste === 'status' || liste === 'trupp') {
                (kataloge[liste] as string[]).push(teile[2]!)
            } else if ((liste === 'stichwoerter' || liste === 'fahrzeuge') && teile.length === 4) {
                const eintraege = kataloge[liste] as Record<string, Record<string, unknown>>
                ;(eintraege[teile[2]!] ??= {id: teile[2]})[teile[3]!] = wert
            }
            continue
        }
        if (teile[0] !== 'alarme' || teile.length < 3) continue

        const alarm: Record<string, never> = (alarme[teile[1]!] ??= {
            id: teile[1], anfahrtsadresse: {}, einsatzadresse: {}, karte: {},
            _hinweise: {}, _gruppen: {},
        } as never)
        const rest = teile.slice(2)
        const kopf = rest[0]!
        if (rest.length === 1) {
            (alarm as Record<string, unknown>)[kopf] = wert
        } else if (kopf === 'anfahrtsadresse' || kopf === 'einsatzadresse' || kopf === 'karte') {
            const unterobjekt = (alarm as never as Record<string, Record<string, unknown>>)[kopf]!
            unterobjekt[rest[1]!] = wert
        } else if (kopf === 'hinweise' && rest.length === 3) {
            const eintraege = (alarm as never as Record<string, Record<string, Record<string, unknown>>>)['_hinweise']!
            ;(eintraege[rest[1]!] ??= {id: rest[1]})[rest[2]!] = wert
        } else if (kopf === 'einsatzmittel' && rest.length >= 3) {
            const gruppen = (alarm as never as Record<string, Record<string, Record<string, unknown>>>)['_gruppen']!
            const gruppe = (gruppen[rest[1]!] ??= {id: rest[1], _fahrzeuge: {}})
            if (rest[2] === 'fahrzeuge' && rest.length === 5) {
                const fahrzeuge = gruppe['_fahrzeuge'] as Record<string, Record<string, unknown>>
                ;(fahrzeuge[rest[3]!] ??= {id: rest[3]})[rest[4]!] = wert
            } else if (rest.length === 3) {
                gruppe[rest[2]!] = wert
            }
        }
    }

    const fertig = geordnet(alarme as never as Record<string, Sortierbar>).map(roh => {
        const alarm = roh as never as Record<string, unknown>
        alarm['hinweise'] = geordnet(alarm['_hinweise'] as Record<string, Sortierbar>)
        alarm['einsatzmittel'] = geordnet(alarm['_gruppen'] as Record<string, Sortierbar>)
            .map(g => {
                const gruppe = g as never as Record<string, unknown>
                gruppe['fahrzeuge'] = geordnet(gruppe['_fahrzeuge'] as Record<string, Sortierbar>)
                delete gruppe['_fahrzeuge']
                return gruppe
            })
        delete alarm['_hinweise']
        delete alarm['_gruppen']
        return alarm
    })

    // Sorted by what they read as, not by their ids, so both sides agree on the order.
    const nachText = (feld: string) => (eintraege: Record<string, Record<string, unknown>>) =>
        Object.values(eintraege).sort((a, b) =>
            String(a[feld] ?? '').localeCompare(String(b[feld] ?? '')) ||
            String(a['id']).localeCompare(String(b['id'])))
    kataloge['fahrzeuge'] = nachText('funkrufname')(
        kataloge['fahrzeuge'] as Record<string, Record<string, unknown>>)
    kataloge['stichwoerter'] = nachText('text')(
        kataloge['stichwoerter'] as Record<string, Record<string, unknown>>)
    for (const liste of ['status', 'trupp'] as const) {
        (kataloge[liste] as string[]).sort()
    }
    return {version: 1, alarme: fertig, kataloge}
}
