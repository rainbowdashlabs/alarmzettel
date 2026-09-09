/**
 * Prüft die Ableitung des Ablaufplans: den Personenplan, die Ortssicht und die acht Prüfungen.
 *
 * Der Personenplan wird nirgends gepflegt, sondern gerechnet — er ist damit genau so richtig wie
 * diese Rechnung. Und die Prüfungen sind der Grund, warum der Plan überhaupt hier und nicht in
 * einer Tabelle entsteht. Beides gehört geprüft, ohne dafür einen Browser zu starten: das Modul
 * kennt weder Store noch Vue, also lässt es sich bündeln und direkt aufrufen.
 *
 *     node tools/ablauf_pruefen.mjs
 */
import {createRequire} from 'node:module'
import {dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'

const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const holen = createRequire(resolve(WURZEL, 'frontend/package.json'))
const {build} = holen('esbuild')

const gebaut = await build({
    entryPoints: [resolve(WURZEL, 'frontend/src/scripts/ablauf.ts')],
    bundle: true, format: 'esm', write: false, platform: 'node',
})
const {lagensicht, ortssicht, personenplan, pruefen} = await import(
    'data:text/javascript;base64,' + Buffer.from(gebaut.outputFiles[0].text).toString('base64'))

const TAG = '2026-09-19'
let laufendeNummer = 0
const kennung = (art) => `${art}-${++laufendeNummer}`

/** Die beiden Orte liegen vier Kilometer auseinander: im Fahrzeug zehn Minuten, zu Fuß sechzig. */
const PUNKTE = {
    'o-nord': {ostwert: 400000, nordwert: 5818000},
    'o-sued': {ostwert: 400000, nordwert: 5814000},
}

function ort(id, name) {
    return {id, sortierung: 0, name, adresse: {}}
}

function person(id, name, felder = {}) {
    return {
        id, sortierung: 0, name, rollen: [], fahrerlaubnis: [], anzahl: 1, verfuegbar: [],
        ...felder,
    }
}

function fahrzeug(id, funkrufname, felder = {}) {
    return {
        id, funkrufname, staerke: '', ezp: '', status: '', plaetze: '', fuehrerschein: '',
        ...felder,
    }
}

function schritt(art, von, bis, ortId, felder = {}) {
    return {
        id: kennung('s'), sortierung: 0, art, mittel: 'fahrzeug',
        von: `${TAG}T${von}`, bis: `${TAG}T${bis}`, ortId, programmpunktId: '',
        besatzung: [], ...felder,
    }
}

function sitzt(personId, faehrt = false) {
    return {id: kennung('b'), sortierung: 0, personId, faehrt}
}

function lauf(fuer, schritte) {
    return {
        id: kennung('l'), sortierung: 0,
        fahrzeugId: fuer.fahrzeugId ?? '', personId: fuer.personId ?? '', schritte,
    }
}

function daten({personen = [], fahrzeuge = [], laeufe = [], programmpunkte = [], orte = []} = {}) {
    return {
        planung: {
            aktiv: true, tage: [{id: 't', sortierung: 0, datum: TAG, name: ''}],
            personen, rollen: [], fahrerlaubnisse: [], programmpunkte, laeufe,
        },
        fahrzeuge,
        orte: orte.length ? orte : [ort('o-nord', 'Wache Nord'), ort('o-sued', 'Kindergarten')],
        punkte: PUNKTE,
    }
}

const faelle = []
const fall = (was, tut) => faelle.push({was, tut})
const arten = (befunde) => befunde.map(befund => befund.art).sort()

fall('Der Personenplan holt die Person aus jeder Kette, in der sie sitzt', () => {
    const alex = person('p-alex', 'Alex')
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const mtf = lauf({fahrzeugId: 'f-mtf'}, [
        schritt('aufenthalt', '10:00', '11:00', 'o-sued', {besatzung: [sitzt('p-alex')]}),
    ])
    const eigen = lauf({personId: 'p-alex'}, [
        schritt('aufenthalt', '09:00', '10:00', 'o-nord'),
    ])
    const plan = personenplan(daten({personen: [alex], laeufe: [mtf, eigen, lhf]}), 'p-alex')
    return [
        ['drei Einträge', plan.length, 3],
        ['nach Zeit sortiert', plan.map(e => e.schritt.von.slice(11)).join(' '),
            '08:00 09:00 10:00'],
        ['und weiß, wo sie fährt', plan.map(e => e.faehrt).join(','), 'true,false,false'],
    ]
})

fall('Eine Fahrt fängt dort an, wo der vorige Schritt endete', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '08:30', '08:40', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const plan = personenplan(daten({personen: [person('p-alex', 'Alex')], laeufe: [kette]}),
        'p-alex')
    return [
        ['die Fahrt geht von Nord los', plan[1].vonOrtId, 'o-nord'],
        ['und kommt in Süd an', plan[1].nachOrtId, 'o-sued'],
    ]
})

fall('Die Ortssicht zeigt, wer gleichzeitig dasteht', () => {
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '09:00', '09:10', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const mimen = lauf({personId: 'p-mimen'}, [
        schritt('aufenthalt', '08:30', '10:00', 'o-sued'),
    ])
    const sicht = ortssicht(daten({laeufe: [lhf, mimen]}), 'o-sued')
    return [
        ['zwei Belegungen', sicht.length, 2],
        ['die Fahrt zählt nicht als Anwesenheit',
            sicht.every(b => b.schritt.art === 'aufenthalt'), true],
        ['die Mimen stehen in ihrer eigenen Kette',
            sicht[1].personIds.join(','), 'p-mimen'],
    ]
})

fall('Mehr Köpfe als Plätze', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('fahrt', '08:00', '08:30', 'o-sued', {
            besatzung: [sitzt('p-alex', true), sitzt('p-mimen')],
        }),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-alex', 'Alex'), person('p-mimen', 'Mimen', {anzahl: 4})],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF', {plaetze: '4'})],
        laeufe: [kette],
    }))
    const zuVoll = befunde.find(b => b.art === 'zuVoll')
    return [
        ['gemeldet', Boolean(zuVoll), true],
        ['fünf Köpfe, vier Plätze', `${zuVoll?.werte.koepfe}/${zuVoll?.werte.plaetze}`, '5/4'],
    ]
})

fall('Genau voll ist noch nicht zu voll', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('fahrt', '08:00', '08:30', 'o-sued', {besatzung: [sitzt('p-mimen', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-mimen', 'Mimen', {anzahl: 4})],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF', {plaetze: '4'})],
        laeufe: [kette],
    }))
    return [['nichts gemeldet', arten(befunde).join(','), '']]
})

fall('Fahrer ohne die Klasse des Fahrzeugs, und Fahrten ohne Fahrer', () => {
    const ohne = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('fahrt', '08:00', '08:30', 'o-sued', {besatzung: [sitzt('p-maria', true)]}),
    ])
    const leer = lauf({fahrzeugId: 'f-mtf'}, [
        schritt('fahrt', '09:00', '09:30', 'o-sued', {besatzung: [sitzt('p-maria')]}),
    ])
    const zwei = lauf({fahrzeugId: 'f-ktw'}, [
        schritt('fahrt', '10:00', '10:30', 'o-sued', {
            besatzung: [sitzt('p-maria', true), sitzt('p-alex', true)],
        }),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-maria', 'Maria', {fahrerlaubnis: ['B']}),
                   person('p-alex', 'Alex', {fahrerlaubnis: ['B', 'C']})],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF', {fuehrerschein: 'C'}), fahrzeug('f-mtf', 'MTF'),
                    fahrzeug('f-ktw', 'KTW')],
        laeufe: [ohne, leer, zwei],
    }))
    const fehlend = befunde.find(b => b.art === 'ohneErlaubnis')
    return [
        ['alle drei gemeldet', arten(befunde).join(','), 'ohneErlaubnis,ohneFahrer,zweiFahrer'],
        ['mit Name und Klasse', `${fehlend?.werte.wer}/${fehlend?.werte.klasse}`, 'Maria/C'],
        ['Alex darf', befunde.some(b => b.personId === 'p-alex'), false],
    ]
})

fall('Zustieg ins Nichts: Maria steigt ein, wo sie nicht ist', () => {
    const eigen = lauf({personId: 'p-maria'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-nord'),
    ])
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '09:00', '09:30', 'o-sued', {besatzung: [sitzt('p-maria', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-maria', 'Maria')],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [eigen, lhf],
    }))
    return [
        ['gemeldet', arten(befunde).join(','), 'zustiegInsNichts'],
        ['am Schritt, in dem sie zusteigt', befunde[0].laufId, lhf.id],
    ]
})

fall('Wird sie abgeholt, ist es kein Zustieg ins Nichts', () => {
    const eigen = lauf({personId: 'p-maria'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-nord'),
    ])
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:40', '09:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '09:00', '09:30', 'o-sued', {
            besatzung: [sitzt('p-alex', true), sitzt('p-maria')],
        }),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-maria', 'Maria'), person('p-alex', 'Alex')],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [eigen, lhf],
    }))
    return [['nichts gemeldet', arten(befunde).join(','), '']]
})

fall('Dieselbe Person zur selben Zeit in zwei Ketten', () => {
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '10:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const mtf = lauf({fahrzeugId: 'f-mtf'}, [
        schritt('aufenthalt', '09:00', '11:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-alex', 'Alex')],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF'), fahrzeug('f-mtf', 'MTF')],
        laeufe: [lhf, mtf],
    }))
    return [
        ['gemeldet', befunde.filter(b => b.art === 'zweiOrte').length, 1],
        ['mit Namen', befunde[0].werte.wer, 'Alex'],
    ]
})

fall('Außerhalb der Verfügbarkeit eingeteilt', () => {
    const spaet = person('p-maria', 'Maria', {
        verfuegbar: [{id: 'v', sortierung: 0, von: `${TAG}T10:00`, bis: `${TAG}T15:00`}],
    })
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-nord', {besatzung: [sitzt('p-maria', true)]}),
        schritt('aufenthalt', '11:00', '12:00', 'o-nord', {besatzung: [sitzt('p-maria', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [spaet], fahrzeuge: [fahrzeug('f-lhf', 'LHF')], laeufe: [lhf],
    }))
    return [
        ['nur der frühe Schritt', befunde.filter(b => b.art === 'ausserhalb').length, 1],
        ['und zwar der um acht',
            lhf.schritte.find(s => s.id === befunde[0].schrittId)?.von.slice(11), '08:00'],
    ]
})

fall('Ohne Verfügbarkeitsfenster ist jemand immer da', () => {
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '05:00', '23:00', 'o-nord', {besatzung: [sitzt('p-maria', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-maria', 'Maria')], fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [lhf],
    }))
    return [['nichts gemeldet', arten(befunde).join(','), '']]
})

fall('Zu knapp geplante Fahrt: vier Kilometer in fünf Minuten', () => {
    const knapp = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '08:30', '08:35', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-alex', 'Alex')], fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [knapp],
    }))
    const zuKnapp = befunde.find(b => b.art === 'zuKnapp')
    return [
        ['gemeldet', Boolean(zuKnapp), true],
        ['fünf statt geschätzter zehn Minuten',
            `${zuKnapp?.werte.geplant}/${zuKnapp?.werte.geschaetzt}`, '5/10'],
    ]
})

fall('Zu Fuß dauert dieselbe Strecke länger', () => {
    const zuFuss = lauf({personId: 'p-maria'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord'),
        schritt('fahrt', '08:30', '09:00', 'o-sued', {mittel: 'fuss'}),
    ])
    const befunde = pruefen(daten({personen: [person('p-maria', 'Maria')], laeufe: [zuFuss]}))
    const zuKnapp = befunde.find(b => b.art === 'zuKnapp')
    return [
        ['dreißig Minuten reichen für vier Kilometer zu Fuß nicht', Boolean(zuKnapp), true],
        ['geschätzt sind sechzig gegen die Fahrzeit von zehn', zuKnapp?.werte.geschaetzt, 60],
    ]
})

fall('Zwei Schritte einer Kette, die sich überschneiden', () => {
    const kaputt = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '08:30', '09:15', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-alex', 'Alex')], fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [kaputt],
    }))
    return [
        ['gemeldet', befunde.filter(b => b.art === 'ueberschneidung').length, 1],
        ['am zweiten Schritt', befunde[0].schrittId, kaputt.schritte[1].id],
    ]
})

fall('Eine Lücke in der Kette ist keine Überschneidung', () => {
    const wartend = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '10:00', '10:30', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-alex', 'Alex')], fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [wartend],
    }))
    return [['nichts gemeldet', arten(befunde).join(','), '']]
})

fall('Zwei ganztägige Ketten melden je Schritt einmal, nicht je Paar', () => {
    const tag = (fahrzeugId) => lauf({fahrzeugId}, [
        schritt('aufenthalt', '08:00', '10:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('aufenthalt', '10:00', '12:00', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-alex', 'Alex')],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF'), fahrzeug('f-mtf', 'MTF')],
        laeufe: [tag('f-lhf'), tag('f-mtf')],
    }))
    return [['zwei Meldungen für zwei überschnittene Schritte',
        befunde.filter(b => b.art === 'zweiOrte').length, 2]]
})

fall('Die Fahrerlaubnis zählt beim Fahren, nicht beim Dastehen', () => {
    const stehend = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-nord', {besatzung: [sitzt('p-maria', true)]}),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-maria', 'Maria', {fahrerlaubnis: ['B']})],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF', {fuehrerschein: 'C'})],
        laeufe: [stehend],
    }))
    return [['nichts gemeldet', arten(befunde).join(','), '']]
})

fall('Über die eigene Anreise wird nichts geschätzt', () => {
    const eigen = lauf({personId: 'p-maria'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord'),
        schritt('fahrt', '08:30', '08:35', 'o-sued', {mittel: 'eigen'}),
    ])
    const befunde = pruefen(daten({personen: [person('p-maria', 'Maria')], laeufe: [eigen]}))
    return [['keine Warnung über zu knapp', arten(befunde).join(','), '']]
})

fall('Eine Lage sammelt ein, was auf sie zeigt', () => {
    const punkt = {id: 'pp-brand', sortierung: 0, name: 'Brand', ortId: 'o-sued', alarmId: ''}
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-sued', {
            programmpunktId: 'pp-brand', besatzung: [sitzt('p-alex', true)],
        }),
    ])
    const mtf = lauf({fahrzeugId: 'f-mtf'}, [
        schritt('aufenthalt', '08:30', '10:00', 'o-sued', {
            programmpunktId: 'pp-brand', besatzung: [sitzt('p-maria', true)],
        }),
    ])
    const mimen = lauf({personId: 'p-mimen'}, [
        schritt('aufenthalt', '07:45', '09:30', 'o-sued', {programmpunktId: 'pp-brand'}),
    ])
    const sicht = lagensicht(daten({
        personen: [person('p-alex', 'Alex'), person('p-maria', 'Maria'),
                   person('p-mimen', 'Mimen', {anzahl: 4})],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF'), fahrzeug('f-mtf', 'MTF')],
        laeufe: [lhf, mtf, mimen], programmpunkte: [punkt],
    }), punkt)
    return [
        ['läuft vom frühesten bis zum spätesten Schritt',
            `${sicht.von.slice(11)}–${sicht.bis.slice(11)}`, '07:45–10:00'],
        ['drei Ketten hängen daran', sicht.laeufe.length, 3],
        ['und alle Beteiligten, jeder einmal',
            sicht.personIds.join(','), 'p-alex,p-maria,p-mimen'],
    ]
})

fall('Eine Lage, auf die kein Schritt zeigt', () => {
    const punkte = [
        {id: 'pp-brand', sortierung: 0, name: 'Brand im Kindergarten', ortId: 'o-sued', alarmId: ''},
        {id: 'pp-rea', sortierung: 0, name: 'Rea', ortId: 'o-nord', alarmId: ''},
    ]
    const lhf = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '09:00', 'o-sued', {
            programmpunktId: 'pp-brand', besatzung: [sitzt('p-alex', true)],
        }),
    ])
    const befunde = pruefen(daten({
        personen: [person('p-alex', 'Alex')], fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [lhf], programmpunkte: punkte,
    }))
    const leer = befunde.filter(b => b.art === 'lageLeer')
    return [
        ['nur die eine', leer.length, 1],
        ['und zwar die Rea', leer[0].programmpunktId, 'pp-rea'],
    ]
})

let fehler = 0
for (const {was, tut} of faelle) {
    console.log(`\n${was}`)
    for (const [name, bekommen, erwartet] of tut()) {
        const gut = bekommen === erwartet
        if (!gut) fehler++
        console.log(`  ${gut ? 'ok  ' : 'FEHL'}  ${name}` +
            (gut ? '' : `: ${JSON.stringify(bekommen)} statt ${JSON.stringify(erwartet)}`))
    }
}

console.log(fehler ? `\n${fehler} Abweichung(en).` : '\nAlles bestanden.')
process.exit(fehler ? 1 : 0)
