/**
 * Druckt Personenplan und Bewegungsbild, wie der Browser sie rechnet, zum Vergleich mit dem
 * Server.
 *
 * Die Ableitung steht zweimal da — in TypeScript für die Ansicht, in Python für das PDF. Solange
 * beide dieselben Zeilen in derselben Reihenfolge liefern, kann der Ausdruck dem Bildschirm nicht
 * widersprechen; das ist der ganze Grund, aus dem beides überhaupt gerechnet und nicht gepflegt
 * wird.
 *
 *     node tools/plan_vergleichen.mjs <arbeitsmappe.json>
 */
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'

const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const holen = createRequire(resolve(WURZEL, 'frontend/package.json'))
const {build} = holen('esbuild')

const quelle = process.argv[2]
if (!quelle) {
    console.error('Aufruf: node tools/plan_vergleichen.mjs <arbeitsmappe.json>')
    process.exit(2)
}

async function laden(pfad) {
    const gebaut = await build({
        entryPoints: [resolve(WURZEL, pfad)],
        bundle: true, format: 'esm', write: false, platform: 'node',
    })
    return import('data:text/javascript;base64,' +
        Buffer.from(gebaut.outputFiles[0].text).toString('base64'))
}

const {anfahrt, einsaetze, einsaetzeAmOrt, fahrzeitSchaetzung, lagenName, personenplan} =
    await laden('frontend/src/scripts/ablauf.ts')
const {bewegungsbild, bewegungstage} = await laden('frontend/src/scripts/bewegungen.ts')

const mappe = JSON.parse(readFileSync(quelle, 'utf8'))
const dienststelle = {
    id: 'wache', sortierung: -1,
    name: mappe.kataloge?.wacheName || 'Dienststelle',
    adresse: mappe.kataloge?.wache ?? {},
}
const orte = [dienststelle, ...(mappe.kataloge?.orte ?? [])]
const punkte = JSON.parse(readFileSync(resolve(quelle, '..', 'punkte.json'), 'utf8'))
const daten = {
    planung: mappe.planung, fahrzeuge: mappe.kataloge?.fahrzeuge ?? [], orte, punkte,
    personen: mappe.kataloge?.personen ?? [],
    alarme: mappe.alarme ?? [],
    kataloge: {material: mappe.kataloge?.material ?? []},
}

const namen = (liste, id, feld) => liste?.find(eintrag => eintrag.id === id)?.[feld] ?? ''
const ort = id => namen(orte, id, 'name')
const lage = id => lagenName(daten, id)
const fahrzeug = id => namen(mappe.kataloge?.fahrzeuge, id, 'funkrufname')
const name = lauf => lauf.fahrzeugId
    ? fahrzeug(lauf.fahrzeugId)
    : namen(mappe.kataloge?.personen, lauf.personId, 'name')

const alleEinsaetze = einsaetze(daten)

for (const person of mappe.kataloge?.personen ?? []) {
    const zeilen = []
    const gesehen = new Set()
    for (const eintrag of personenplan(daten, person.id)) {
        const schritt = eintrag.schritt
        const weg = eintrag.vonOrtId === schritt.ortId ? null : anfahrt(daten, eintrag.lauf, schritt)
        if (weg && schritt.art === 'aufenthalt') {
            zeilen.push([
                weg.von.slice(0, 10), weg.von.slice(11, 16), weg.bis.slice(11, 16), 'fahrt',
                ort(weg.vonOrtId), ort(weg.nachOrtId), '',
                eintrag.faehrt ? 'faehrt' : '-', fahrzeug(eintrag.lauf.fahrzeugId),
                fahrzeitSchaetzung(daten, eintrag.lauf, schritt) ?? '-',
            ])
        }
        zeilen.push([
            schritt.von.slice(0, 10), eintrag.ankunft.slice(11, 16), eintrag.bis.slice(11, 16),
            schritt.art, ort(schritt.art === 'fahrt' ? eintrag.vonOrtId : schritt.ortId),
            ort(eintrag.nachOrtId),
            lage(schritt.programmpunktId),
            eintrag.faehrt ? 'faehrt' : '-', fahrzeug(eintrag.lauf.fahrzeugId),
            schritt.art === 'aufenthalt'
                ? '-' : fahrzeitSchaetzung(daten, eintrag.lauf, schritt) ?? '-',
        ])
        for (const einsatz of einsaetzeAmOrt(eintrag, alleEinsaetze)) {
            const schluessel = `${einsatz.programmpunkt.id}-${einsatz.nummer}`
            if (gesehen.has(schluessel)) continue
            gesehen.add(schluessel)
            zeilen.push([
                einsatz.da.slice(0, 10), einsatz.da.slice(11, 16), einsatz.bis.slice(11, 16),
                'einsatz', ort(einsatz.ortId), ort(einsatz.ortId), '', '-',
                [...new Set(einsatz.beteiligte
                    .filter(teil => teil.aufgebot)
                    .map(teil => fahrzeug(teil.lauf.fahrzeugId))
                    .filter(Boolean))].join(', '),
                '-',
            ])
        }
    }
    zeilen.sort((a, b) => a[0] === b[0] ? (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0)
                                        : (a[0] < b[0] ? -1 : 1))
    for (const felder of zeilen) console.log(['PLAN', person.name, ...felder].join(' | '))
}

for (const einsatz of einsaetze(daten)) {
    console.log([
        'EINSATZ', lage(einsatz.programmpunkt.id), einsatz.nummer, einsatz.ortId,
        einsatz.von, einsatz.da, einsatz.bis,
        einsatz.beteiligte
            .map(eintrag => `${name(eintrag.lauf)}${eintrag.aufgebot ? '' : '*'}`).join(','),
    ].join(' | '))
}
