import type {Arbeitsmappe} from '../interfaces/Alarm'

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
    for (const liste of ['stichwoerter', 'status', 'trupp'] as const) {
        for (const wert of mappe.kataloge[liste]) werte[pfad('kataloge', liste, wert)] = true
    }
    for (const vorlage of mappe.kataloge.fahrzeuge) {
        const vbasis = pfad('kataloge', 'fahrzeuge', vorlage.funkrufname)
        for (const feld of ['funkrufname', 'staerke', 'ezp', 'status'] as const) {
            werte[pfad(vbasis, feld)] = vorlage[feld] ?? ''
        }
    }
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
        stichwoerter: [] as string[], status: [] as string[], trupp: [] as string[],
        fahrzeuge: {} as Record<string, unknown>, arbeitsgruppe: '',
    }

    for (const [schluessel, wert] of Object.entries(werte)) {
        const teile = schluessel.split(TRENNER)
        if (teile[0] === 'kataloge' && teile.length === 2) {
            kataloge[teile[1]!] = wert
            continue
        }
        if (teile[0] === 'kataloge' && teile.length >= 3) {
            const liste = teile[1]!
            if (liste === 'stichwoerter' || liste === 'status' || liste === 'trupp') {
                (kataloge[liste] as string[]).push(teile[2]!)
            } else if (liste === 'fahrzeuge' && teile.length === 4) {
                const gruppe = kataloge['fahrzeuge'] as Record<string, Record<string, unknown>>
                ;(gruppe[teile[2]!] ??= {})[teile[3]!] = wert
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

    kataloge['fahrzeuge'] = Object.keys(kataloge['fahrzeuge'] as object).sort()
        .map(name => (kataloge['fahrzeuge'] as Record<string, unknown>)[name])
    for (const liste of ['stichwoerter', 'status', 'trupp'] as const) {
        (kataloge[liste] as string[]).sort()
    }
    return {version: 1, alarme: fertig, kataloge}
}
