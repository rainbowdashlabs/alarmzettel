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

const FAHRZEUGFELDER =
    ['funkrufname', 'staerke', 'ezp', 'status', 'plaetze', 'fuehrerschein'] as const

const KATALOGWORTLISTEN = ['status', 'trupp', 'rollen', 'fahrerlaubnisse'] as const

/** Was einmal im Plan stand und heute im Katalog. Der alte Pfad wird beim Lesen umgesetzt. */
const UMGEZOGEN = ['orte', 'tage', 'personen', 'rollen', 'fahrerlaubnisse']

/**
 * Jede Liste des Plans mit den Feldern, die als Pfad je Eintrag geschrieben werden. Was darunter
 * hängt — Adresse, Verfügbarkeit, Schritte, Besatzung — steht in `planungsfelder`. Spiegelt
 * `PLANUNGSEINTRAEGE` in `backend/src/data/dokument.py`.
 */
const PLANUNGSEINTRAEGE = {
    programmpunkte: ['name', 'alarmId'],
    laeufe: ['fahrzeugId', 'personId'],
} as const

/** Die Tage und das Personal stehen im Katalog; die Verfügbarkeiten hängen unter der Person. */
const KATALOGEINTRAEGE = {
    tage: ['datum', 'name'],
    personen: ['name', 'anzahl'],
} as const

const SCHRITTFELDER = ['art', 'mittel', 'fahrzeit', 'von', 'bis', 'ortId', 'programmpunktId',
    'aufgebot', 'notiz'] as const

type Eintragsdaten = Record<string, unknown> & { id: string, sortierung?: number }

/**
 * Was ein Feld bedeutet, das eine ältere Arbeitsmappe noch gar nicht kannte. Für Text ist das der
 * leere String; ein Wahrheitswert und eine Anzahl brauchen ihre eigene Vorgabe, sonst käme ein
 * leerer String zurück, den das Modell weder als Ja oder Nein noch als Zahl lesen kann.
 */
const VORGABEN: Record<string, unknown> = {aufgebot: true, faehrt: false, anzahl: 1, fahrzeit: 0}

function eintragsfelder(basis: string, werte: Flachbild, eintrag: Eintragsdaten,
                        felder: readonly string[], stelle: number) {
    werte[pfad(basis, 'sortierung')] = eintrag.sortierung ?? stelle
    for (const feld of felder) {
        werte[pfad(basis, feld)] = eintrag[feld] ?? VORGABEN[feld] ?? ''
    }
}

/**
 * Den Plan flach machen. Die Ketten sind das Tiefste im Dokument — Lauf, Schritt, Besatzung — und
 * jede Ebene trägt ihre eigene id, damit zwei Leute an verschiedenen Schritten desselben Laufs
 * arbeiten können, ohne sich zu überschreiben.
 */
/** Tage und Personal — die Verfügbarkeiten und die Wortmengen hängen unter der Person. */
function katalogeintraege(werte: Flachbild, kataloge: Record<string, unknown>) {
    for (const [liste, felder] of Object.entries(KATALOGEINTRAEGE)) {
        const eintraege = (kataloge[liste] ?? []) as Eintragsdaten[]
        eintraege.forEach((eintrag, stelle) => {
            const basis = pfad('kataloge', liste, eintrag.id)
            eintragsfelder(basis, werte, eintrag, felder, stelle)
            if (liste !== 'personen') return
            for (const satz of ['rollen', 'fahrerlaubnis'] as const) {
                for (const wert of (eintrag[satz] ?? []) as string[]) {
                    werte[pfad(basis, satz, wert)] = true
                }
            }
            ;((eintrag.verfuegbar ?? []) as Eintragsdaten[]).forEach((fenster, platz) => {
                eintragsfelder(pfad(basis, 'verfuegbar', fenster.id), werte, fenster,
                               ['von', 'bis'], platz)
            })
        })
    }
}

function planungsfelder(werte: Flachbild, planung: Planung) {
    werte[pfad('planung', 'aktiv')] = planung.aktiv ?? false

    for (const [liste, felder] of Object.entries(PLANUNGSEINTRAEGE)) {
        const eintraege = (planung[liste as keyof Planung] ?? []) as unknown as Eintragsdaten[]
        eintraege.forEach((eintrag, stelle) => {
            const basis = pfad('planung', liste, eintrag.id)
            eintragsfelder(basis, werte, eintrag, felder, stelle)

            if (liste === 'laeufe') {
                ;((eintrag.schritte ?? []) as Eintragsdaten[]).forEach((schritt, platz) => {
                    const sbasis = pfad(basis, 'schritte', schritt.id)
                    eintragsfelder(sbasis, werte, schritt, SCHRITTFELDER, platz)
                    ;((schritt.besatzung ?? []) as Eintragsdaten[]).forEach((sitzt, rang) => {
                        eintragsfelder(pfad(sbasis, 'besatzung', sitzt.id), werte, sitzt,
                                       ['personId', 'faehrt'], rang)
                    })
                    ;((schritt.material ?? []) as Eintragsdaten[]).forEach((stueck, rang) => {
                        eintragsfelder(pfad(sbasis, 'material', stueck.id), werte, stueck,
                                       ['materialId', 'anzahl'], rang)
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

        ;(alarm.hinweise ?? []).forEach((hinweis, stelle) => {
            const hbasis = pfad(basis, 'hinweise', hinweis.id)
            werte[pfad(hbasis, 'sortierung')] = hinweis.sortierung ?? stelle
            for (const [feld, wert] of Object.entries(hinweis)) {
                if (feld !== 'id' && feld !== 'sortierung') werte[pfad(hbasis, feld)] = wert
            }
        })

        ;(alarm.einsatzmittel ?? []).forEach((gruppe, stelle) => {
            const gbasis = pfad(basis, 'einsatzmittel', gruppe.id)
            werte[pfad(gbasis, 'sortierung')] = gruppe.sortierung ?? stelle
            werte[pfad(gbasis, 'gruppe')] = gruppe.gruppe ?? ''
            ;(gruppe.fahrzeuge ?? []).forEach((fahrzeug, platz) => {
                const fbasis = pfad(gbasis, 'fahrzeuge', fahrzeug.id)
                werte[pfad(fbasis, 'sortierung')] = fahrzeug.sortierung ?? platz
                for (const [feld, wert] of Object.entries(fahrzeug)) {
                    if (feld !== 'id' && feld !== 'sortierung') werte[pfad(fbasis, feld)] = wert
                }
            })
        })
    })

    werte[pfad('kataloge', 'arbeitsgruppe')] = mappe.kataloge.arbeitsgruppe ?? ''
    werte[pfad('kataloge', 'wacheName')] = mappe.kataloge.wacheName ?? ''
    werte[pfad('kataloge', 'alarmeProTag')] = mappe.kataloge.alarmeProTag ?? 2200
    adresse(pfad('kataloge', 'wache'), werte, mappe.kataloge.wache as never)
    // Status and Trupp are words and nothing else, so the word is its own key. Stichwörter and
    // vehicles are pointed at by the Alarme, so they are keyed by an id that a rename survives.
    for (const liste of KATALOGWORTLISTEN) {
        for (const wert of mappe.kataloge[liste] ?? []) werte[pfad('kataloge', liste, wert)] = true
    }
    for (const eintrag of mappe.kataloge.stichwoerter ?? []) {
        werte[pfad('kataloge', 'stichwoerter', eintrag.id, 'text')] = eintrag.text ?? ''
    }
    for (const stueck of mappe.kataloge.material ?? []) {
        werte[pfad('kataloge', 'material', stueck.id, 'name')] = stueck.name ?? ''
        werte[pfad('kataloge', 'material', stueck.id, 'bestand')] = stueck.bestand ?? 0
    }
    for (const vorlage of mappe.kataloge.fahrzeuge ?? []) {
        const vbasis = pfad('kataloge', 'fahrzeuge', vorlage.id)
        for (const feld of FAHRZEUGFELDER) werte[pfad(vbasis, feld)] = vorlage[feld] ?? ''
    }
    ;(mappe.kataloge.orte ?? []).forEach((ort, stelle) => {
        const obasis = pfad('kataloge', 'orte', ort.id)
        werte[pfad(obasis, 'sortierung')] = ort.sortierung ?? stelle
        werte[pfad(obasis, 'name')] = ort.name ?? ''
        adresse(pfad(obasis, 'adresse'), werte, ort.adresse as never)
    })
    katalogeintraege(werte, mappe.kataloge as unknown as Record<string, unknown>)
    if (mappe.planung) planungsfelder(werte, mappe.planung)
    return werte
}

type Sortierbar = { id: string, sortierung?: number }

function geordnet<T extends Sortierbar>(eintraege: Record<string, T>): T[] {
    return Object.values(eintraege).sort(
        (a, b) => (a.sortierung ?? 0) - (b.sortierung ?? 0) || a.id.localeCompare(b.id))
}

type Sammlung = Record<string, Record<string, unknown>>

/**
 * Einen Pfad des Plans zurück in die geschachtelte Form legen. Die Ebenen unter einem Eintrag
 * heißen hier `_…`, solange sie noch nach id geschlüsselt sind; `rund` macht am Ende sortierte
 * Listen daraus. Spiegelt `_planung_lesen` in `backend/src/data/dokument.py`.
 */
/** Einen Pfad des Katalogs zurücklegen, soweit er einen Eintrag mit Unterlisten meint. */
function katalogLesen(kataloge: Record<string, unknown>, rest: string[], wert: unknown) {
    if (rest.length < 2 || !(rest[0]! in KATALOGEINTRAEGE)) return
    const sammlung = kataloge[rest[0]!] as Sammlung
    const eintrag = (sammlung[rest[1]!] ??= {id: rest[1]})
    const tiefer = rest.slice(2)
    if (tiefer.length === 1) {
        eintrag[tiefer[0]!] = wert
    } else if ((tiefer[0] === 'rollen' || tiefer[0] === 'fahrerlaubnis') && tiefer.length === 2) {
        ((eintrag[tiefer[0]] ??= []) as string[]).push(tiefer[1]!)
    } else if (tiefer[0] === 'verfuegbar' && tiefer.length === 3) {
        const fenster = (eintrag._verfuegbar ??= {}) as Sammlung
        ;(fenster[tiefer[1]!] ??= {id: tiefer[1]})[tiefer[2]!] = wert
    }
}

function planungLesen(planung: Record<string, unknown>, rest: string[], wert: unknown) {
    if (!rest.length) return
    if (rest.length === 1) {
        planung[rest[0]!] = wert
        return
    }
    if (!(rest[0]! in PLANUNGSEINTRAEGE)) return

    const sammlung = planung[rest[0]!] as Sammlung
    const eintrag = (sammlung[rest[1]!] ??= {id: rest[1]})
    const tiefer = rest.slice(2)
    if (tiefer.length === 1) {
        eintrag[tiefer[0]!] = wert
    } else if (tiefer[0] === 'schritte' && tiefer.length >= 3) {
        const schritte = (eintrag._schritte ??= {}) as Sammlung
        const schritt = (schritte[tiefer[1]!] ??= {id: tiefer[1]})
        if (tiefer.length === 3) {
            schritt[tiefer[2]!] = wert
        } else if (tiefer[2] === 'material' && tiefer.length === 5) {
            const material = (schritt._material ??= {}) as Sammlung
            ;(material[tiefer[3]!] ??= {id: tiefer[3]})[tiefer[4]!] = wert
        } else if (tiefer[2] === 'besatzung' && tiefer.length === 5) {
            const besatzung = (schritt._besatzung ??= {}) as Sammlung
            ;(besatzung[tiefer[3]!] ??= {id: tiefer[3]})[tiefer[4]!] = wert
        }
    }
}

export function rund(werte: Flachbild): unknown {
    const alarme: Record<string, Record<string, never>> = {}
    const planung: Record<string, unknown> = {
        aktiv: false,
        ...Object.fromEntries(Object.keys(PLANUNGSEINTRAEGE).map(liste => [liste, {}])),
    }
    const kataloge: Record<string, unknown> = {
        stichwoerter: {} as Record<string, Record<string, unknown>>,
        fahrzeuge: {} as Record<string, Record<string, unknown>>,
        orte: {} as Record<string, Record<string, unknown>>,
        material: {} as Record<string, Record<string, unknown>>,
        arbeitsgruppe: '', wache: {} as Record<string, unknown>, wacheName: '',
        alarmeProTag: 2200,
        ...Object.fromEntries(KATALOGWORTLISTEN.map(liste => [liste, [] as string[]])),
        ...Object.fromEntries(Object.keys(KATALOGEINTRAEGE).map(liste => [liste, {}])),
    }

    for (const [schluessel, wert] of Object.entries(werte)) {
        let teile = schluessel.split(TRENNER)
        // Orte, Tage, Personal und die Wortlisten standen einmal im Plan. Die alten Pfade
        // behalten ihre Bedeutung, sonst verlöre eine bestehende Sitzung sie; geschrieben werden
        // sie nicht mehr.
        if (teile[0] === 'planung' && UMGEZOGEN.includes(teile[1] ?? '')) {
            teile = ['kataloge', ...teile.slice(1)]
        } else if (teile[0] === 'planung') {
            planungLesen(planung, teile.slice(1), wert)
            continue
        }
        if (teile[0] === 'kataloge' && teile.length === 2) {
            kataloge[teile[1]!] = wert
            continue
        }
        if (teile[0] === 'kataloge' && teile.length >= 3) {
            const liste = teile[1]!
            if (liste === 'wache' && teile.length === 3) {
                (kataloge['wache'] as Record<string, unknown>)[teile[2]!] = wert
            } else if ((KATALOGWORTLISTEN as readonly string[]).includes(liste)) {
                (kataloge[liste] as string[]).push(teile[2]!)
            } else if (liste in KATALOGEINTRAEGE) {
                katalogLesen(kataloge, teile.slice(1), wert)
            } else if ((liste === 'stichwoerter' || liste === 'fahrzeuge' || liste === 'material')
                       && teile.length === 4) {
                const eintraege = kataloge[liste] as Record<string, Record<string, unknown>>
                ;(eintraege[teile[2]!] ??= {id: teile[2]})[teile[3]!] = wert
            } else if (liste === 'orte' && teile.length >= 4) {
                const eintraege = kataloge['orte'] as Record<string, Record<string, unknown>>
                const ort = (eintraege[teile[2]!] ??= {id: teile[2], adresse: {}})
                if (teile[3] === 'adresse' && teile.length === 5) {
                    (ort['adresse'] as Record<string, unknown>)[teile[4]!] = wert
                } else if (teile.length === 4) {
                    ort[teile[3]!] = wert
                }
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
    kataloge['material'] = nachText('name')(
        kataloge['material'] as Record<string, Record<string, unknown>>)
    for (const liste of KATALOGWORTLISTEN) {
        (kataloge[liste] as string[]).sort()
    }

    const nachSortierung = (eintraege: Sammlung) => geordnet(eintraege as never as Record<string, Sortierbar>)
    kataloge['orte'] = nachSortierung(kataloge['orte'] as Sammlung)
    for (const liste of Object.keys(KATALOGEINTRAEGE)) {
        kataloge[liste] = nachSortierung(kataloge[liste] as Sammlung)
    }
    for (const person of kataloge.personen as Record<string, unknown>[]) {
        person.verfuegbar = nachSortierung((person._verfuegbar ?? {}) as Sammlung)
        delete person._verfuegbar
    }
    for (const liste of Object.keys(PLANUNGSEINTRAEGE)) {
        planung[liste] = nachSortierung(planung[liste] as Sammlung)
    }
    for (const lauf of planung.laeufe as Record<string, unknown>[]) {
        const schritte = nachSortierung((lauf._schritte ?? {}) as Sammlung) as Record<string, unknown>[]
        for (const schritt of schritte) {
            schritt.besatzung = nachSortierung((schritt._besatzung ?? {}) as Sammlung)
            delete schritt._besatzung
            schritt.material = nachSortierung((schritt._material ?? {}) as Sammlung)
            delete schritt._material
        }
        lauf.schritte = schritte
        delete lauf._schritte
    }
    return {version: 1, alarme: fertig, kataloge, planung}
}
