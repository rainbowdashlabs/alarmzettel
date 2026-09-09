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

const {personenplan} = await laden('frontend/src/scripts/ablauf.ts')
const {bewegungsbild, bewegungstage} = await laden('frontend/src/scripts/bewegungen.ts')

const mappe = JSON.parse(readFileSync(quelle, 'utf8'))
const daten = {planung: mappe.planung, fahrzeuge: mappe.kataloge?.fahrzeuge ?? []}

const namen = (liste, id, feld) => liste?.find(eintrag => eintrag.id === id)?.[feld] ?? ''
const ort = id => namen(mappe.planung.orte, id, 'name')
const lage = id => namen(mappe.planung.programmpunkte, id, 'name')
const fahrzeug = id => namen(mappe.kataloge?.fahrzeuge, id, 'funkrufname')

for (const person of mappe.planung.personen ?? []) {
    for (const eintrag of personenplan(daten, person.id)) {
        console.log([
            'PLAN', person.name,
            eintrag.schritt.von.slice(0, 10), eintrag.schritt.von.slice(11, 16),
            eintrag.schritt.bis.slice(11, 16), eintrag.schritt.art,
            ort(eintrag.vonOrtId), ort(eintrag.nachOrtId), lage(eintrag.schritt.programmpunktId),
            eintrag.faehrt ? 'faehrt' : '-', fahrzeug(eintrag.lauf.fahrzeugId),
        ].join(' | '))
    }
}

for (const tag of bewegungstage(daten)) {
    const bild = bewegungsbild(daten, tag)
    console.log(['FENSTER', bild.datum, bild.von, bild.bis].join(' | '))
    for (const band of bild.baender) {
        console.log(['BAND', bild.datum, band.name, band.reihen].join(' | '))
    }
    for (const balken of bild.balken) {
        console.log(['BALKEN', bild.datum, balken.schrittId, balken.ortId, balken.reihe,
                     balken.von, balken.bis, balken.name, balken.besatzung.join(','),
                     balken.lage].join(' | '))
    }
    for (const linie of bild.linien) {
        console.log(['LINIE', bild.datum, linie.schrittId, linie.vonOrtId, linie.vonReihe,
                     linie.nachOrtId, linie.nachReihe, linie.von, linie.bis, linie.mittel,
                     linie.name].join(' | '))
    }
}
