/**
 * Prüft das Bewegungsbild, den Stand zu einem Zeitpunkt und die Umrechnung der Koordinaten.
 *
 * Das Bild ordnet Bänder und Reihen an, die Lagekarte fragt „wer ist gerade wo“, und beides hängt
 * daran, dass aus den amtlichen UTM-Werten dieselben Punkte werden, die der Berliner Dienst in
 * WGS 84 ausgibt. Alle drei rechnen ohne Browser, also lassen sie sich hier prüfen.
 *
 *     node tools/bewegungen_pruefen.mjs
 */
import {createRequire} from 'node:module'
import {dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'

const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const holen = createRequire(resolve(WURZEL, 'frontend/package.json'))
const {build} = holen('esbuild')

async function laden(pfad) {
    const gebaut = await build({
        entryPoints: [resolve(WURZEL, pfad)],
        bundle: true, format: 'esm', write: false, platform: 'node',
    })
    return import('data:text/javascript;base64,' +
        Buffer.from(gebaut.outputFiles[0].text).toString('base64'))
}

const {bewegungsbild, bewegungstage, ereignisse, materialstand, standorte} =
    await laden('frontend/src/scripts/bewegungen.ts')
const {utm33ZuWgs84, wgs84ZuUtm33} = await laden('frontend/src/scripts/geo.ts')

const TAG = '2026-09-19'
let nummer = 0
const kennung = (art) => `${art}-${++nummer}`

const ort = (id, name) => ({id, sortierung: 0, name, adresse: {}})
const person = (id, name, felder = {}) =>
    ({id, sortierung: 0, name, rollen: [], fahrerlaubnis: [], anzahl: 1, verfuegbar: [], ...felder})
const fahrzeug = (id, funkrufname) =>
    ({id, funkrufname, staerke: '', ezp: '', status: '', plaetze: '', fuehrerschein: ''})
const sitzt = (personId, faehrt = false) =>
    ({id: kennung('b'), sortierung: 0, personId, faehrt})

function schritt(art, von, bis, ortId, felder = {}) {
    const [vonTag, vonZeit] = von.includes('T') ? von.split('T') : [TAG, von]
    const [bisTag, bisZeit] = bis.includes('T') ? bis.split('T') : [TAG, bis]
    return {
        id: kennung('s'), sortierung: 0, art, mittel: 'fahrzeug',
        von: `${vonTag}T${vonZeit}`, bis: `${bisTag}T${bisZeit}`, ortId, programmpunktId: '',
        aufgebot: true, notiz: '', besatzung: [], material: [], ...felder,
    }
}

const lauf = (fuer, schritte) => ({
    id: kennung('l'), sortierung: 0,
    fahrzeugId: fuer.fahrzeugId ?? '', personId: fuer.personId ?? '', schritte,
})

const posten = (materialId, anzahl = 1) => ({id: kennung('m'), sortierung: 0, materialId, anzahl})

function daten({personen = [], fahrzeuge = [], laeufe = [], programmpunkte = [], orte,
                material = []} = {}) {
    return {
        planung: {
            aktiv: true, programmpunkte, laeufe,
        },
        fahrzeuge,
        personen,
        orte: orte ?? [ort('o-nord', 'Wache Nord'), ort('o-sued', 'Kindergarten')],
        kataloge: {material},
    }
}

const faelle = []
const fall = (was, tut) => faelle.push({was, tut})

fall('Jeder Ort wird ein Band, in der Reihenfolge der Stammdaten', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-sued'),
        schritt('fahrt', '08:30', '08:45', 'o-nord'),
        schritt('aufenthalt', '08:45', '10:00', 'o-nord'),
    ])
    const bild = bewegungsbild(daten({fahrzeuge: [fahrzeug('f-lhf', 'LHF')], laeufe: [kette]}), TAG)
    return [
        ['beide Orte, in der Reihenfolge der Stammdaten',
            bild.baender.map(band => band.name).join(','), 'Wache Nord,Kindergarten'],
        ['das Fenster liegt auf vollen Stunden', `${bild.von}–${bild.bis}`, '480–600'],
        ['zwei Balken und eine Linie',
            `${bild.balken.length}/${bild.linien.length}`, '2/1'],
    ]
})

fall('Ein Ort, an dem an diesem Tag nichts geschieht, bekommt kein Band', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [schritt('aufenthalt', '08:00', '09:00', 'o-nord')])
    const bild = bewegungsbild(daten({
        fahrzeuge: [fahrzeug('f-lhf', 'LHF')], laeufe: [kette],
        orte: [ort('o-nord', 'Wache Nord'), ort('o-sued', 'Kindergarten'),
               ort('o-leer', 'Nie besucht')],
    }), TAG)
    return [['nur das eine Band', bild.baender.map(band => band.name).join(','), 'Wache Nord']]
})

fall('Was gleichzeitig dasteht, bekommt eigene Reihen; was nacheinander steht, teilt sich eine', () => {
    const zugleich = daten({
        fahrzeuge: [fahrzeug('f-a', 'A'), fahrzeug('f-b', 'B')],
        laeufe: [
            lauf({fahrzeugId: 'f-a'}, [schritt('aufenthalt', '08:00', '10:00', 'o-nord')]),
            lauf({fahrzeugId: 'f-b'}, [schritt('aufenthalt', '09:00', '11:00', 'o-nord')]),
        ],
    })
    const nacheinander = daten({
        fahrzeuge: [fahrzeug('f-a', 'A'), fahrzeug('f-b', 'B')],
        laeufe: [
            lauf({fahrzeugId: 'f-a'}, [schritt('aufenthalt', '08:00', '09:00', 'o-nord')]),
            lauf({fahrzeugId: 'f-b'}, [schritt('aufenthalt', '09:00', '10:00', 'o-nord')]),
        ],
    })
    return [
        ['übereinander zwei Reihen', bewegungsbild(zugleich, TAG).baender[0].reihen, 2],
        ['nacheinander eine', bewegungsbild(nacheinander, TAG).baender[0].reihen, 1],
        ['und die Balken liegen in Reihe 0 und 1',
            bewegungsbild(zugleich, TAG).balken.map(b => b.reihe).join(','), '0,1'],
    ]
})

fall('Eine Fahrt verbindet die Reihen, in denen sie abfährt und ankommt', () => {
    const halter = lauf({fahrzeugId: 'f-a'}, [schritt('aufenthalt', '07:00', '12:00', 'o-sued')])
    const kette = lauf({fahrzeugId: 'f-b'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord'),
        schritt('fahrt', '08:30', '08:45', 'o-sued'),
        schritt('aufenthalt', '08:45', '10:00', 'o-sued'),
    ])
    const bild = bewegungsbild(daten({
        fahrzeuge: [fahrzeug('f-a', 'A'), fahrzeug('f-b', 'B')], laeufe: [halter, kette],
    }), TAG)
    const linie = bild.linien[0]
    return [
        ['sie geht von Wache Nord nach Kindergarten',
            `${linie.vonOrtId}→${linie.nachOrtId}`, 'o-nord→o-sued'],
        ['aus Reihe 0 in die freie Reihe 1', `${linie.vonReihe}→${linie.nachReihe}`, '0→1'],
    ]
})

fall('Jeder Tag bekommt sein eigenes Bild', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '2026-09-19T08:00', '2026-09-19T09:00', 'o-nord'),
        schritt('aufenthalt', '2026-09-20T08:00', '2026-09-20T09:00', 'o-sued'),
    ])
    const gesetzt = daten({fahrzeuge: [fahrzeug('f-lhf', 'LHF')], laeufe: [kette]})
    return [
        ['zwei Tage', bewegungstage(gesetzt).join(','), '2026-09-19,2026-09-20'],
        ['und je Tag, was an ihm geschieht — auch die Wache, von der die Anfahrt herführt',
            bewegungsbild(gesetzt, '2026-09-20').baender.map(b => b.name).join(','),
            'Wache Nord,Kindergarten'],
    ]
})

fall('Dasselbe je Person erzählt: das Fahrzeug wird zur Begleitung', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '08:30', '08:45', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
        schritt('aufenthalt', '08:45', '10:00', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const eigene = lauf({personId: 'p-mimen'}, [
        schritt('aufenthalt', '07:30', '10:00', 'o-sued'),
    ])
    const gesetzt = daten({
        personen: [person('p-alex', 'Alex'), person('p-mimen', 'Mimen', {anzahl: 4})],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF')], laeufe: [kette, eigene],
    })
    const bild = bewegungsbild(gesetzt, TAG, 'personen')
    const alex = bild.balken.filter(balken => balken.name === 'Alex')
    return [
        ['Alex ist eine eigene Spur', alex.length, 2],
        ['und fährt im LHF', alex[1].begleitung.join(','), 'LHF'],
        ['die Mimen stehen für sich', bild.balken.find(b => b.name === 'Mimen').begleitung.length, 0],
        ['seine Fahrt zieht von Band zu Band',
            bild.linien.filter(l => l.name === 'Alex').length, 1],
        ['und im Fahrzeugbild ist es umgekehrt: das LHF trägt seine Besatzung',
            bewegungsbild(gesetzt, TAG).balken.find(b => b.name === 'LHF').begleitung.join(','),
            'Alex'],
    ]
})

fall('Der Stand zu einem Zeitpunkt: stehend, unterwegs, gar nicht da', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord', {besatzung: [sitzt('p-alex', true)]}),
        schritt('fahrt', '08:30', '08:50', 'o-sued', {besatzung: [sitzt('p-alex', true)]}),
    ])
    const gesetzt = daten({
        personen: [person('p-alex', 'Alex')], fahrzeuge: [fahrzeug('f-lhf', 'LHF')],
        laeufe: [kette],
    })
    const stehend = standorte(gesetzt, `${TAG}T08:10`)
    const fahrend = standorte(gesetzt, `${TAG}T08:35`)
    return [
        ['um 08:10 steht es an der Wache', stehend[0].ortId, 'o-nord'],
        ['mit seiner Besatzung', stehend[0].personen.join(','), 'Alex'],
        ['um 08:35 ist es unterwegs', fahrend[0].ortId, ''],
        ['ein Viertel der Strecke', fahrend[0].unterwegs.anteil, 0.25],
        ['vorher ist nichts zu sehen', standorte(gesetzt, `${TAG}T07:00`).length, 0],
        ['und danach auch nicht', standorte(gesetzt, `${TAG}T09:00`).length, 0],
    ]
})

fall('Die nächsten Ereignisse stehen in der Reihenfolge, in der sie eintreten', () => {
    const eins = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord'),
        schritt('fahrt', '08:30', '08:45', 'o-sued'),
        schritt('aufenthalt', '08:45', '10:00', 'o-sued', {programmpunktId: 'pp'}),
    ])
    const zwei = lauf({personId: 'p-mimen'}, [
        schritt('aufenthalt', '08:40', '09:00', 'o-sued'),
    ])
    const gesetzt = daten({
        personen: [person('p-mimen', 'Mimen', {anzahl: 4})],
        fahrzeuge: [fahrzeug('f-lhf', 'LHF')], laeufe: [eins, zwei],
        programmpunkte: [{id: 'pp', sortierung: 0, name: 'Brand', ortId: 'o-sued', alarmId: ''}],
    })
    const kommend = ereignisse(gesetzt, `${TAG}T08:05`)
    return [
        ['drei stehen noch aus', kommend.length, 3],
        ['die Abfahrt zuerst', `${kommend[0].art} ${kommend[0].in}`, 'abfahrt 25'],
        ['dann die Mimen', `${kommend[1].name} ${kommend[1].in}`, 'Mimen 35'],
        ['und die Lage trägt ihren Namen', kommend[2].lage, 'Brand'],
        ['was schon läuft, steht nicht mehr an',
            ereignisse(gesetzt, `${TAG}T09:00`).length, 0],
    ]
})

fall('Material liegt irgendwo oder ist unterwegs — der Plan sagt es von selbst', () => {
    const kette = lauf({fahrzeugId: 'f-lhf'}, [
        schritt('aufenthalt', '08:00', '08:30', 'o-nord', {material: [posten('m-puppe', 4)]}),
        schritt('fahrt', '08:30', '08:50', 'o-sued', {material: [posten('m-puppe', 4)]}),
        schritt('aufenthalt', '08:50', '10:00', 'o-sued', {material: [posten('m-puppe', 4)]}),
    ])
    const gesetzt = daten({
        fahrzeuge: [fahrzeug('f-lhf', 'LHF')], laeufe: [kette],
        material: [{id: 'm-puppe', name: 'Übungspuppe'}, {id: 'm-nebel', name: 'Nebelmaschine'}],
    })
    const liegend = materialstand(gesetzt, `${TAG}T08:10`)
    const fahrend = materialstand(gesetzt, `${TAG}T08:40`)
    return [
        ['um 08:10 liegt die Puppe an der Wache', liegend[0].ortId, 'o-nord'],
        ['und zwar vier Stück', liegend[0].anzahl, 4],
        ['und nichts ist unterwegs', liegend[0].unterwegs, null],
        ['um 08:40 fährt sie mit dem LHF', fahrend[0].traeger, 'LHF'],
        ['auf halber Strecke zum Kindergarten',
            `${fahrend[0].unterwegs.anteil} → ${fahrend[0].unterwegs.nachOrtId}`, '0.5 → o-sued'],
        ['die Nebelmaschine ist nirgends eingeplant und taucht nicht auf',
            liegend.map(stand => stand.name).join(), 'Übungspuppe'],
        ['vor dem ersten Schritt liegt nichts',
            materialstand(gesetzt, `${TAG}T07:00`).length, 0],
    ]
})

// Der Berliner Adressdienst gibt dieselben Punkte in beiden Systemen aus; das sind die Zahlen.
const KOORDINATEN = [
    ['Junker-Jörg-Straße 36', {ostwert: 399598.791, nordwert: 5815944.114}, 52.48439726, 13.52144944],
    ['Archenholdstraße 21', {ostwert: 398470.239, nordwert: 5818552.633}, 52.50763155, 13.50404047],
    ['Platz der Republik 1', {ostwert: 389775.529, nordwert: 5819960.354}, 52.51859372, 13.37551809],
]

fall('UTM 33N wird zu denselben Punkten, die der Dienst in WGS 84 nennt', () =>
    KOORDINATEN.map(([was, punkt, breite, laenge]) => {
        const marke = utm33ZuWgs84(punkt)
        const nord = (marke.breite - breite) * 111320
        const ost = (marke.laenge - laenge) * 111320 * Math.cos(breite * Math.PI / 180)
        return [`${was}: unter einem Zentimeter daneben`, Math.hypot(nord, ost) < 0.01, true]
    }))

fall('Und dieselbe Projektion vorwärts, zurück auf die amtlichen Werte', () =>
    KOORDINATEN.map(([was, punkt, breite, laenge]) => {
        const zurueck = wgs84ZuUtm33({breite, laenge})
        const weite = Math.hypot(zurueck.ostwert - punkt.ostwert,
                                 zurueck.nordwert - punkt.nordwert)
        return [`${was}: unter einem Zentimeter daneben`, weite < 0.01, true]
    }))

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
