/**
 * Prints what the browser's flattener makes of a working set, so it can be compared with what the
 * server makes of it. The two implementations have to agree exactly: a path only one side knows
 * would look to the other like an entry that was never there.
 *
 *     node tools/pfade_vergleichen.mjs <arbeitsmappe.json> [--rund]
 *
 * `--rund` prints the working set rebuilt from those paths instead. Comparing only the paths
 * leaves the way back untested — a flattener that writes a path its own rebuilder ignores passes
 * the path check and still loses that data on every sync.
 */
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'

const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), '..')

// Node resolves an import from the importing file's directory, and esbuild is installed for the
// frontend. Anchoring the lookup at the frontend's package.json finds it from here.
const holen = createRequire(resolve(WURZEL, 'frontend/package.json'))
const {build} = holen('esbuild')

const quelle = process.argv[2]
if (!quelle) {
    console.error('Aufruf: node tools/pfade_vergleichen.mjs <arbeitsmappe.json>')
    process.exit(2)
}

const gebaut = await build({
    entryPoints: [resolve(WURZEL, 'frontend/src/scripts/flach.ts')],
    bundle: true, format: 'esm', write: false, platform: 'node',
})
const modul = await import(
    'data:text/javascript;base64,' + Buffer.from(gebaut.outputFiles[0].text).toString('base64'))

const mappe = JSON.parse(readFileSync(quelle, 'utf8'))

// The browser states a list's order by the order of the list; the server stamps that into the
// sort key on the way in, so the same has to happen here or the two sides differ on it alone.
mappe.alarme.forEach((alarm, stelle) => {
    alarm.sortierung = stelle
    ;(alarm.hinweise ?? []).forEach((hinweis, platz) => (hinweis.sortierung = platz))
    ;(alarm.einsatzmittel ?? []).forEach((gruppe, platz) => {
        gruppe.sortierung = platz
        ;(gruppe.fahrzeuge ?? []).forEach((fahrzeug, rang) => (fahrzeug.sortierung = rang))
    })
})

/** Schlüssel sortiert, damit der Vergleich vom Inhalt handelt und nicht von der Reihenfolge. */
function geordnet(wert) {
    if (Array.isArray(wert)) return wert.map(geordnet)
    if (wert && typeof wert === 'object') {
        return Object.fromEntries(Object.keys(wert).sort().map(k => [k, geordnet(wert[k])]))
    }
    return wert
}

if (process.argv.includes('--rund')) {
    process.stdout.write(JSON.stringify(geordnet(modul.rund(modul.flach(mappe))), null, 1) + '\n')
} else {
    for (const pfad of Object.keys(modul.flach(mappe)).sort()) {
        process.stdout.write(pfad.split(modul.TRENNER).join(' / ') + '\n')
    }
}
