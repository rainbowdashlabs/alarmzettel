/**
 * Runs the browser's own sync module outside a browser, twice, against a live server.
 *
 * The merge was verified on the server side by unit tests, and the two flatteners were shown to
 * agree by tools/pfade_vergleichen. What neither covers is the client half: the shadow copy, the
 * difference it sends and the way an incoming change is folded back in. That is also where the
 * bugs were. So this bundles `frontend/src/store/sync.ts` — the real one, not a reimplementation
 * — gives it the handful of browser globals it touches, and drives two independent instances
 * through the situations two people actually get into.
 *
 *     node tools/sync_probe.mjs        (PORT_PROBE setzt den Port, Vorgabe 8131)
 */

import {spawn} from 'node:child_process'
import {mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs'
import {tmpdir} from 'node:os'
import {createRequire} from 'node:module'
import {dirname, resolve} from 'node:path'
import {fileURLToPath, pathToFileURL} from 'node:url'

const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const holen = createRequire(resolve(WURZEL, 'frontend/package.json'))
const {build} = holen('esbuild')

// axios reaches for Node builtins through a CommonJS shim, and an ESM bundle has no `require`
// to give it. This hands it a real one; it resolves against the bundle's own file, which is why
// each client is written to disk rather than imported from a data: URL.
const BANNER = {js: "import {createRequire as __cr} from 'node:module';" +
    "const require = __cr(import.meta.url);"}

const HAFEN = Number(process.env.PORT_PROBE ?? 8131)
const basis = `http://127.0.0.1:${HAFEN}`
const ABLAGE = mkdtempSync(resolve(tmpdir(), 'alarmzettel-sync-'))

/**
 * The probe brings its own server and its own share directory. It deletes and resurrects things,
 * which is not something to do to a workspace anyone is using, and both are gone again when it
 * ends, however it ends.
 */
let dienst

process.on('exit', () => {
    if (dienst && !dienst.killed) dienst.kill('SIGTERM')
    rmSync(ABLAGE, {recursive: true, force: true})
})
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => process.exit(1))

async function serverStarten() {
    dienst = spawn('uvicorn',
        ['--app-dir', 'backend/src', 'main:app', '--host', '127.0.0.1',
         '--port', String(HAFEN), '--log-level', 'warning'],
        {
            cwd: WURZEL,
            env: {...process.env, SITZUNG_VERZEICHNIS: resolve(ABLAGE, 'sitzungen')},
            stdio: ['ignore', 'ignore', 'inherit'],
        })

    for (let versuch = 0; versuch < 60; versuch++) {
        await new Promise((fertig) => setTimeout(fertig, 500))
        try {
            if ((await fetch(`${basis}/api/health`)).ok) return
        } catch { /* not up yet */ }
    }
    throw new Error(`Der Prüfserver auf Port ${HAFEN} kam nicht hoch.`)
}

/** The browser globals the module reaches for. Each client gets its own storage, as tabs do. */
function umgebung() {
    const ablage = new Map()
    return {
        localStorage: {
            getItem: (schluessel) => (ablage.has(schluessel) ? ablage.get(schluessel) : null),
            setItem: (schluessel, wert) => ablage.set(schluessel, String(wert)),
            removeItem: (schluessel) => ablage.delete(schluessel),
        },
        window: {setTimeout, clearTimeout, setInterval, clearInterval},
    }
}

/**
 * A fresh instance of the module. ES modules are cached per URL, so each client gets its own
 * source text and with it its own shadow copy and its own view of the working set.
 */
async function klient(name) {
    const umfeld = umgebung()
    globalThis.localStorage = umfeld.localStorage
    globalThis.window = umfeld.window
    // Each client is bundled to its own file, which is what gives it its own module instance
    // and with it its own shadow copy.
    const quelle = [
        `// ${name}`,
        `export * from ${JSON.stringify(resolve(WURZEL, 'frontend/src/store/sync.ts'))}`,
        `export {arbeitsmappe} from ${JSON.stringify(
            resolve(WURZEL, 'frontend/src/store/arbeitsmappe.ts'))}`,
    ].join('\n')
    const gebautJe = await build({
        stdin: {contents: quelle, resolveDir: WURZEL, loader: 'ts'},
        bundle: true, format: 'esm', write: false, platform: 'node', banner: BANNER,
        define: {'import.meta.env': JSON.stringify({VITE_API_BASE_URL: basis})},
    })
    const datei = resolve(ABLAGE, `${name}.mjs`)
    writeFileSync(datei, gebautJe.outputFiles[0].text)
    let modul
    try {
        modul = await import(pathToFileURL(datei).href)
    } catch (fehler) {
        console.error(`Klient ${name} liess sich nicht laden: ${fehler.message}`)
        console.error(String(fehler.stack).split('\n').slice(1, 4).join('\n'))
        process.exit(1)
    }
    return {name, ...modul, umfeld}
}

const warten = (ms) => new Promise((fertig) => setTimeout(fertig, ms))

let fehlgeschlagen = 0

function pruefe(behauptung, bedingung, gefunden) {
    if (bedingung) {
        console.log(`  ok    ${behauptung}`)
    } else {
        fehlgeschlagen += 1
        console.log(`  FEHLT ${behauptung}${gefunden === undefined ? '' : ` — ${gefunden}`}`)
    }
}

await serverStarten()

const angelegt = await fetch(`${basis}/api/sitzung`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: readFileSync(resolve(WURZEL, 'backend/src/render/sample/sample.json'), 'utf8'),
})
const {token} = await angelegt.json()

const anna = await klient('anna')
const ben = await klient('ben')

globalThis.localStorage = anna.umfeld.localStorage
globalThis.window = anna.umfeld.window
await anna.beitreten(token, 'Anna')

globalThis.localStorage = ben.umfeld.localStorage
globalThis.window = ben.umfeld.window
await ben.beitreten(token, 'Ben')

/** Runs one client's exchange with its own globals in place. */
async function abgleichen(klientIn) {
    globalThis.localStorage = klientIn.umfeld.localStorage
    globalThis.window = klientIn.umfeld.window
    await klientIn.jetztAbgleichen()
}

const alarmVon = (klientIn) => klientIn.arbeitsmappe.alarme[0]

console.log('\nBeitreten')
pruefe('Anna sieht den Alarm', alarmVon(anna) !== undefined,
    `${anna.arbeitsmappe.alarme.length} Alarme`)
pruefe('Ben sieht denselben Alarm', alarmVon(ben)?.id === alarmVon(anna)?.id)
pruefe('beide sehen dasselbe Stichwort', alarmVon(ben)?.stichwort === alarmVon(anna)?.stichwort,
    `${alarmVon(anna)?.stichwort} / ${alarmVon(ben)?.stichwort}`)

console.log('\nZwei Felder desselben Alarms, gleichzeitig')
alarmVon(anna).stichwort = 'TH 2 VON ANNA'
alarmVon(ben).anrufer = 'Von Ben eingetragen'
await abgleichen(anna)
await abgleichen(ben)
await abgleichen(anna)
pruefe('Annas Stichwort steht bei Ben', alarmVon(ben).stichwort === 'TH 2 VON ANNA',
    alarmVon(ben).stichwort)
pruefe('Bens Anrufer steht bei Anna', alarmVon(anna).anrufer === 'Von Ben eingetragen',
    alarmVon(anna).anrufer)
pruefe('Annas eigene Änderung bleibt bei ihr', alarmVon(anna).stichwort === 'TH 2 VON ANNA')

console.log('\nEine Änderung während eine andere unterwegs ist')
alarmVon(anna).kurzinfo = 'Anna tippt weiter'
const unterwegs = (async () => {
    globalThis.localStorage = ben.umfeld.localStorage
    globalThis.window = ben.umfeld.window
    alarmVon(ben).betroffener = 'Ben schreibt zeitgleich'
    await ben.jetztAbgleichen()
})()
await abgleichen(anna)
await unterwegs
await abgleichen(anna)
await abgleichen(ben)
pruefe('Annas Kurzinfo überlebt', alarmVon(anna).kurzinfo === 'Anna tippt weiter',
    alarmVon(anna).kurzinfo)
pruefe('Bens Betroffener überlebt', alarmVon(anna).betroffener === 'Ben schreibt zeitgleich',
    alarmVon(anna).betroffener)

console.log('\nNeuer Alarm bei Anna')
const vorher = ben.arbeitsmappe.alarme.length
anna.arbeitsmappe.alarme.push({
    ...JSON.parse(JSON.stringify(alarmVon(anna))),
    id: 'zweiter-alarm', sortierung: 5, stichwort: 'BRAND 2', hinweise: [], einsatzmittel: [],
})
await abgleichen(anna)
await abgleichen(ben)
pruefe('Ben bekommt den neuen Alarm', ben.arbeitsmappe.alarme.length === vorher + 1,
    `${ben.arbeitsmappe.alarme.length} Alarme`)
pruefe('mit dem richtigen Stichwort',
    ben.arbeitsmappe.alarme.some((a) => a.stichwort === 'BRAND 2'))

console.log('\nBen löscht, Anna kennt die Löschung noch nicht')
ben.arbeitsmappe.alarme = ben.arbeitsmappe.alarme.filter((a) => a.id !== 'zweiter-alarm')
if (process.env.SPUR) console.log('   Ben vor dem Senden:', ben.arbeitsmappe.alarme.map(a => a.id))
await abgleichen(ben)
if (process.env.SPUR) console.log('   Ben nach dem Senden:', ben.arbeitsmappe.alarme.map(a => a.id))
const beiAnna = anna.arbeitsmappe.alarme.find((a) => a.id === 'zweiter-alarm')
if (beiAnna) beiAnna.anrufer = 'Anna ändert einen gelöschten Alarm'
await abgleichen(anna)
if (process.env.SPUR) console.log('   nach Annas Abgleich, Anna:', anna.arbeitsmappe.alarme.map(a => a.id))
if (process.env.SPUR) {
    const vorher = Object.keys(ben.schatten()).filter(p => p.includes('zweiter-alarm'))
    console.log(`   Bens Schatten vor dem Abgleich: ${vorher.length} Pfade zu zweiter-alarm`)
}
await abgleichen(ben)
if (process.env.SPUR) {
    const nachher = Object.keys(ben.schatten()).filter(p => p.includes('zweiter-alarm'))
    console.log(`   Bens Schatten danach: ${nachher.length} Pfade`,
        nachher.slice(0, 3).map(p => p.split(String.fromCharCode(31)).join('/')))
    console.log('   nach Bens Abgleich, Ben:', ben.arbeitsmappe.alarme.map(a => a.id))
}
pruefe('der Alarm bleibt bei Ben gelöscht',
    !ben.arbeitsmappe.alarme.some((a) => a.id === 'zweiter-alarm'),
    `${ben.arbeitsmappe.alarme.length} Alarme`)
pruefe('und kommt bei Anna nicht zurück',
    !anna.arbeitsmappe.alarme.some((a) => a.id === 'zweiter-alarm'),
    `${anna.arbeitsmappe.alarme.length} Alarme`)

console.log('\nHinweise als Liste')
const hinweise = alarmVon(anna).hinweise
const zahlVorher = hinweise.length
hinweise.push({id: 'neuer-hinweis', sortierung: 99, typ: 'text', text: 'Von Anna ergänzt'})
await abgleichen(anna)
await abgleichen(ben)
pruefe('Ben sieht den neuen Hinweis',
    alarmVon(ben).hinweise.some((h) => h.text === 'Von Anna ergänzt'),
    `${alarmVon(ben).hinweise.length} Hinweise`)
pruefe('die vorhandenen bleiben', alarmVon(ben).hinweise.length === zahlVorher + 1)

const ersterHinweis = alarmVon(ben).hinweise[0]
alarmVon(ben).hinweise = alarmVon(ben).hinweise.filter((h) => h.id !== ersterHinweis.id)
alarmVon(anna).hinweise.find((h) => h.id === 'neuer-hinweis').text = 'Von Anna geändert'
await abgleichen(ben)
await abgleichen(anna)
await abgleichen(ben)
pruefe('gelöschter Hinweis bleibt weg',
    !alarmVon(anna).hinweise.some((h) => h.id === ersterHinweis.id))
pruefe('gleichzeitig geänderter Hinweis überlebt',
    alarmVon(ben).hinweise.find((h) => h.id === 'neuer-hinweis')?.text === 'Von Anna geändert')

console.log('\nDie Liste läuft leer und füllt sich wieder')
// Wird der letzte Eintrag einer Liste gelöscht, ist die Liste selbst vollständig verschwunden.
// Ein Grabstein darauf würde sie zumauern: der Server hält alles unterhalb eines Grabsteins für
// gelöscht, und kein späterer Eintrag käme je wieder hinein.
alarmVon(anna).hinweise = []
await abgleichen(anna)
await abgleichen(ben)
pruefe('leergeräumte Liste kommt bei beiden leer an',
    alarmVon(anna).hinweise.length === 0 && alarmVon(ben).hinweise.length === 0)

alarmVon(anna).hinweise.push({id: 'nach-dem-leeren', sortierung: 0, typ: 'text',
    text: 'Nach dem Leerräumen'})
await abgleichen(anna)
await abgleichen(ben)
pruefe('und nimmt danach wieder etwas auf',
    alarmVon(ben).hinweise.some((h) => h.text === 'Nach dem Leerräumen'),
    `${alarmVon(ben).hinweise.length} Hinweise bei Ben`)

console.log('\nVerbindung weg und wieder da')
alarmVon(anna).meldender = 'Während der Störung getippt'
const echtesFetch = globalThis.fetch
globalThis.fetch = undefined
try {
    await abgleichen(anna)
} catch { /* the module swallows it; this is only in case it does not */ }
globalThis.fetch = echtesFetch
pruefe('das Getippte ist noch da', alarmVon(anna).meldender === 'Während der Störung getippt')
await abgleichen(anna)
await abgleichen(ben)
pruefe('und erreicht Ben nach dem Abgleich',
    alarmVon(ben).meldender === 'Während der Störung getippt', alarmVon(ben).meldender)

console.log('\nAbgleich vor dem Drucken')
// What the PDF buttons rely on: they exchange before they render, so the sheet is made from
// what everyone has. Ben writes, Anna does not wait for the next beat but flushes and reads.
alarmVon(ben).stichwort = 'BRAND 4 KURZ VOR DEM DRUCK'
await abgleichen(ben)
pruefe('Anna hat die Änderung vor dem Abgleich noch nicht',
    alarmVon(anna).stichwort !== 'BRAND 4 KURZ VOR DEM DRUCK', alarmVon(anna).stichwort)
await abgleichen(anna)
pruefe('nach dem Abgleich steht sie in Annas Arbeitsmappe',
    alarmVon(anna).stichwort === 'BRAND 4 KURZ VOR DEM DRUCK', alarmVon(anna).stichwort)

console.log('\nBeide Seiten am Ende gleich')
await abgleichen(anna)
await abgleichen(ben)
await abgleichen(anna)
const alsText = (klientIn) => JSON.stringify(klientIn.arbeitsmappe.alarme)
pruefe('Anna und Ben sehen dasselbe', alsText(anna) === alsText(ben))

/**
 * Everything the server holds has to match what the browser shows. Not the other way round: the
 * browser fills in the fields of an Alarm that were never set, and those were never sent.
 */
function abweichung(erwartet, gefunden, wo = '') {
    if (Array.isArray(erwartet)) {
        if (!Array.isArray(gefunden) || gefunden.length !== erwartet.length) {
            return `${wo}: ${erwartet.length} statt ${gefunden?.length}`
        }
        return erwartet.map((e, i) => abweichung(e, gefunden[i], `${wo}[${i}]`)).find(Boolean)
    }
    if (erwartet && typeof erwartet === 'object') {
        return Object.keys(erwartet)
            .map((k) => abweichung(erwartet[k], gefunden?.[k], `${wo}.${k}`))
            .find(Boolean)
    }
    return erwartet === gefunden ? undefined : `${wo}: "${erwartet}" statt "${gefunden}"`
}

const server = await (await fetch(`${basis}/api/sitzung/${token}`)).json()
const unterschiedZumServer = abweichung(server.arbeitsmappe.alarme, anna.arbeitsmappe.alarme)
pruefe('und der Server dasselbe wie beide', unterschiedZumServer === undefined,
    unterschiedZumServer)

await warten(50)
console.log(fehlgeschlagen === 0 ? '\nAlles bestanden.' : `\n${fehlgeschlagen} fehlgeschlagen.`)
process.exit(fehlgeschlagen === 0 ? 0 : 1)
