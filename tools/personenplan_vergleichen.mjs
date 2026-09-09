/**
 * Druckt den Personenplan, wie der Browser ihn rechnet, zum Vergleich mit dem des Servers.
 *
 * Die Ableitung steht zweimal da — in TypeScript für die Ansicht, in Python für das PDF. Solange
 * beide dieselben Zeilen in derselben Reihenfolge liefern, kann der Zettel dem Bildschirm nicht
 * widersprechen; das ist der ganze Grund, aus dem der Personenplan überhaupt gerechnet und nicht
 * gepflegt wird.
 *
 *     node tools/personenplan_vergleichen.mjs <arbeitsmappe.json>
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
    console.error('Aufruf: node tools/personenplan_vergleichen.mjs <arbeitsmappe.json>')
    process.exit(2)
}

const gebaut = await build({
    entryPoints: [resolve(WURZEL, 'frontend/src/scripts/ablauf.ts')],
    bundle: true, format: 'esm', write: false, platform: 'node',
})
const {personenplan} = await import(
    'data:text/javascript;base64,' + Buffer.from(gebaut.outputFiles[0].text).toString('base64'))

const mappe = JSON.parse(readFileSync(quelle, 'utf8'))
const daten = {planung: mappe.planung, fahrzeuge: mappe.kataloge?.fahrzeuge ?? []}

const namen = (liste, id, feld) => liste?.find(eintrag => eintrag.id === id)?.[feld] ?? ''
const ort = id => namen(mappe.planung.orte, id, 'name')
const lage = id => namen(mappe.planung.programmpunkte, id, 'name')
const fahrzeug = id => namen(mappe.kataloge?.fahrzeuge, id, 'funkrufname')

for (const person of mappe.planung.personen ?? []) {
    for (const eintrag of personenplan(daten, person.id)) {
        console.log([
            person.name,
            eintrag.schritt.von.slice(0, 10), eintrag.schritt.von.slice(11, 16),
            eintrag.schritt.bis.slice(11, 16), eintrag.schritt.art,
            ort(eintrag.vonOrtId), ort(eintrag.nachOrtId), lage(eintrag.schritt.programmpunktId),
            eintrag.faehrt ? 'faehrt' : '-', fahrzeug(eintrag.lauf.fahrzeugId),
        ].join(' | '))
    }
}
