/**
 * Checks the Polar-Koordinaten against the values a real slip carries.
 *
 * The rule was not documented anywhere — it was recovered from two printed slips by solving for
 * the point both bearings and distances agree on, which turned out to be the station itself. That
 * makes these numbers the only specification there is, so they are worth a test.
 *
 *     node tools/polar_pruefen.mjs
 */
import {createRequire} from 'node:module'
import {dirname, resolve} from 'node:path'
import {fileURLToPath} from 'node:url'

const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const holen = createRequire(resolve(WURZEL, 'frontend/package.json'))
const {build} = holen('esbuild')

const gebaut = await build({
    entryPoints: [resolve(WURZEL, 'frontend/src/scripts/polar.ts')],
    bundle: true, format: 'esm', write: false, platform: 'node',
})
const {polarKoordinaten} = await import(
    'data:text/javascript;base64,' + Buffer.from(gebaut.outputFiles[0].text).toString('base64'))

// Feuerwache Karlshorst, Junker-Jörg-Straße 36, from the Berlin address register.
const WACHE = {ostwert: 399598.791, nordwert: 5815944.114}

const FAELLE = [
    {
        was: 'Archenholdstraße 21, 10315',
        ziel: {ostwert: 398470.239, nordwert: 5818552.633},
        // The slip prints 336,6°/2,849 km. The bearing matches to the digit; the seven metres are
        // the difference between the register's point for the station and whatever the dispatch
        // system measures from, and are below what the sheet would show as a change in bearing.
        erwartet: '336,6°/2,842 km',
    },
    {
        was: 'unter einem Kilometer führt die Null als Leerzeichen',
        ziel: {ostwert: 399598.791 + 60.7, nordwert: 5815944.114 + 340.6},
        erwartet: '10,1°/ ,346 km',
    },
    {
        was: 'die Wache selbst',
        ziel: WACHE,
        erwartet: '0,0°/ ,000 km',
    },
]

let fehler = 0
for (const fall of FAELLE) {
    const bekommen = polarKoordinaten(WACHE, fall.ziel)
    const gut = bekommen === fall.erwartet
    if (!gut) fehler++
    console.log(`  ${gut ? 'ok  ' : 'FEHL'}  ${fall.was}: ${JSON.stringify(bekommen)}` +
        (gut ? '' : ` statt ${JSON.stringify(fall.erwartet)}`))
}

console.log(fehler ? `\n${fehler} Abweichung(en).` : '\nAlles bestanden.')
process.exit(fehler ? 1 : 0)
