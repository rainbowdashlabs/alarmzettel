<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import SchrittFenster from './SchrittFenster.vue'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {
  einordnen, laufSichern, laufVon, lageName, materialName, ortName, personName, plandaten,
  schrittMitZeit,
} from '../../store/planung'
import {anfahrt, personenplan} from '../../scripts/ablauf'
import {alsMinuten, tagVon, verschieben, zeitpunkt} from '../../scripts/zeit'
import type {Lauf, Schritt} from '../../interfaces/Planung'

/**
 * Der Tag als Kalender: senkrecht die Zeit, je Fahrzeug und Person eine Spalte. Ein Aufenthalt
 * wird aufgezogen wie ein Termin, verschoben wie einer, und was in ihm steckt, steht auf der
 * Kachel — geändert wird er im Fenster.
 *
 * Die Kette bleibt dabei eine Folge: ein verschobener Block rückt auch in ihr an seine Stelle,
 * sonst zeigte die erzeugte Anfahrt auf den falschen Vorgänger.
 */
const PX_JE_MINUTE = 1.1
const RASTER = 5
/** Ein aufgezogener Block unter dieser Länge war ein Klick daneben. */
const KUERZESTE = 10
const VORGABEFENSTER = {von: 6 * 60, bis: 20 * 60}

const tag = ref('')
const auswahl = ref<{ lauf: Lauf, schritt: Schritt, name: string } | null>(null)
const gitter = ref<HTMLElement | null>(null)

/** Alle Tage, an denen etwas steht, dazu die des Katalogs — der leere Tag will bepflanzt werden. */
const tage = computed(() => {
  const gefunden = new Set(arbeitsmappe.kataloge.tage.map(eintrag => eintrag.datum))
  for (const lauf of arbeitsmappe.planung.laeufe) {
    for (const schritt of lauf.schritte) {
      const wann = tagVon(schritt.von)
      if (wann) gefunden.add(wann)
    }
  }
  gefunden.delete('')
  return [...gefunden].sort()
})

watch(tage, liste => {
  if (!liste.includes(tag.value)) tag.value = liste[0] ?? ''
}, {immediate: true})

const heute = computed(() => tag.value || new Date().toISOString().slice(0, 10))

interface Kachel {
  lauf: Lauf
  schritt: Schritt
  von: number
  bis: number
  /** Minute, ab der man wirklich da ist; davor liegt die erzeugte Anfahrt. */
  da: number
  /** Ein Schritt einer anderen Kette, in dem diese Person nur mitfährt. */
  fremd: boolean
}

interface Spalte {
  schluessel: string
  name: string
  art: 'fahrzeug' | 'person'
  fuer: { fahrzeugId?: string, personId?: string }
  lauf: Lauf | undefined
  kacheln: Kachel[]
}

function minute(wann: string): number {
  const wert = alsMinuten(wann)
  const beginn = alsMinuten(`${heute.value}T00:00`)
  return wert === null || beginn === null ? 0 : wert - beginn
}

function amTag(schritt: Schritt): boolean {
  return tagVon(schritt.von) === heute.value
}

function kachel(lauf: Lauf, schritt: Schritt, fremd: boolean): Kachel {
  const weg = anfahrt(plandaten(), lauf, schritt)
  return {
    lauf, schritt, von: minute(schritt.von), bis: minute(schritt.bis),
    da: minute(weg?.bis ?? schritt.von), fremd,
  }
}

const spalten = computed<Spalte[]>(() => {
  const daten = plandaten()
  const gefunden: Spalte[] = []
  for (const fahrzeug of arbeitsmappe.kataloge.fahrzeuge) {
    const lauf = laufVon({fahrzeugId: fahrzeug.id})
    gefunden.push({
      schluessel: `f-${fahrzeug.id}`, name: fahrzeug.funkrufname || t('ablauf.ohneName'),
      art: 'fahrzeug', fuer: {fahrzeugId: fahrzeug.id}, lauf,
      kacheln: (lauf?.schritte ?? []).filter(amTag).map(schritt => kachel(lauf!, schritt, false)),
    })
  }
  for (const person of arbeitsmappe.kataloge.personen) {
    const lauf = laufVon({personId: person.id})
    const kacheln = personenplan(daten, person.id)
      .filter(eintrag => amTag(eintrag.schritt))
      .map(eintrag => kachel(eintrag.lauf, eintrag.schritt, Boolean(eintrag.lauf.fahrzeugId)))
    gefunden.push({
      schluessel: `p-${person.id}`, name: person.name || t('ablauf.ohneName'),
      art: 'person', fuer: {personId: person.id}, lauf, kacheln,
    })
  }
  return gefunden
})

/** Das Fenster liegt auf vollen Stunden und umfasst, was an diesem Tag geplant ist. */
const fenster = computed(() => {
  const zeiten = spalten.value.flatMap(spalte =>
      spalte.kacheln.flatMap(eintrag => [eintrag.von, eintrag.bis]))
  if (!zeiten.length) return VORGABEFENSTER
  const von = Math.min(VORGABEFENSTER.von, Math.floor(Math.min(...zeiten) / 60) * 60)
  const bis = Math.max(VORGABEFENSTER.bis, Math.ceil(Math.max(...zeiten) / 60) * 60)
  return {von, bis}
})

const stunden = computed(() => {
  const reihen: number[] = []
  for (let wann = fenster.value.von; wann < fenster.value.bis; wann += 60) reihen.push(wann)
  return reihen
})

const hoehe = computed(() => (fenster.value.bis - fenster.value.von) * PX_JE_MINUTE)

function oben(minuten: number): number {
  return (minuten - fenster.value.von) * PX_JE_MINUTE
}

function beschriftung(minuten: number): string {
  const innerhalb = ((minuten % 1440) + 1440) % 1440
  return `${String(Math.floor(innerhalb / 60)).padStart(2, '0')}:` +
      String(innerhalb % 60).padStart(2, '0')
}

/** Wo im Tag der Zeiger steht, auf fünf Minuten gerastert. */
function minuteAus(ereignis: PointerEvent): number {
  const flaeche = gitter.value?.getBoundingClientRect()
  if (!flaeche) return fenster.value.von
  const roh = fenster.value.von + (ereignis.clientY - flaeche.top) / PX_JE_MINUTE
  const gerastert = Math.round(roh / RASTER) * RASTER
  return Math.min(Math.max(gerastert, fenster.value.von), fenster.value.bis)
}

function alsZeitpunkt(minuten: number): string {
  return verschieben(zeitpunkt(heute.value, '00:00'), minuten)
}

type Griff = 'neu' | 'schieben' | 'ende'

const zug = ref<{
  art: Griff
  spalte: Spalte
  schritt?: Schritt
  lauf?: Lauf
  anker: number
  start: number
  laenge: number
  von: number
  bis: number
  bewegt: boolean
} | null>(null)

const vorschau = computed(() => zug.value?.art === 'neu' ? zug.value : null)

/**
 * Gezogen wird am Fenster und nicht am Element: die Unterkante ist ein eigener Griff, und wer
 * über die Spalte hinausfährt, soll den Block trotzdem weiterschieben.
 */
function fassen(ereignis: PointerEvent, art: Griff, spalte: Spalte, kachel?: Kachel) {
  if (ereignis.button !== 0) return
  const jetzt = minuteAus(ereignis)
  zug.value = {
    art, spalte, schritt: kachel?.schritt, lauf: kachel?.lauf,
    anker: kachel ? jetzt - kachel.von : jetzt,
    start: jetzt,
    laenge: kachel ? kachel.bis - kachel.von : 0,
    von: kachel?.von ?? jetzt, bis: kachel?.bis ?? jetzt,
    bewegt: false,
  }
  window.addEventListener('pointermove', ziehen)
  window.addEventListener('pointerup', loslassen)
  window.addEventListener('pointercancel', loslassen)
  ereignis.preventDefault()
}

function ziehen(ereignis: PointerEvent) {
  const lauf = zug.value
  if (!lauf) return
  const jetzt = minuteAus(ereignis)
  lauf.bewegt = lauf.bewegt || Math.abs(jetzt - lauf.start) >= RASTER
  if (lauf.art === 'neu') {
    lauf.von = Math.min(lauf.anker, jetzt)
    lauf.bis = Math.max(lauf.anker, jetzt)
    return
  }
  if (!lauf.schritt) return
  if (lauf.art === 'ende') {
    lauf.bis = Math.max(jetzt, lauf.von + RASTER)
  } else {
    lauf.von = jetzt - lauf.anker
    lauf.bis = lauf.von + lauf.laenge
  }
  lauf.schritt.von = alsZeitpunkt(lauf.von)
  lauf.schritt.bis = alsZeitpunkt(lauf.bis)
}

function loslassen() {
  window.removeEventListener('pointermove', ziehen)
  window.removeEventListener('pointerup', loslassen)
  window.removeEventListener('pointercancel', loslassen)
  const lauf = zug.value
  zug.value = null
  if (!lauf) return
  if (lauf.art === 'neu') {
    if (lauf.bis - lauf.von < KUERZESTE) return
    const kette = laufSichern(lauf.spalte.fuer)
    const schritt = schrittMitZeit(kette, alsZeitpunkt(lauf.von), alsZeitpunkt(lauf.bis))
    auswahl.value = {lauf: kette, schritt, name: kettenName(kette)}
    return
  }
  if (!lauf.schritt || !lauf.lauf) return
  if (!lauf.bewegt) {
    auswahl.value = {lauf: lauf.lauf, schritt: lauf.schritt, name: kettenName(lauf.lauf)}
    return
  }
  einordnen(lauf.lauf, lauf.schritt)
}

/**
 * Der Schritt gehört der Kette, in der er steht — auch wenn er in der Spalte einer Person liegt,
 * die in ihr mitfährt. Das Fenster nennt deshalb die Kette und nicht die Spalte.
 */
function oeffnen(kachel: Kachel) {
  auswahl.value = {lauf: kachel.lauf, schritt: kachel.schritt, name: kettenName(kachel.lauf)}
}

function kettenName(lauf: Lauf): string {
  return (lauf.fahrzeugId
      ? arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === lauf.fahrzeugId)?.funkrufname
      : personName(lauf.personId)) || t('ablauf.ohneName')
}

/** Was auf der Kachel steht, ohne sie zu öffnen. */
function stichworte(kachel: Kachel): string[] {
  const zeilen = [ortName(kachel.schritt.ortId) || t('ablauf.ohneName')]
  const lage = lageName(kachel.schritt.programmpunktId)
  if (lage) zeilen.push(lage)
  if (kachel.lauf.fahrzeugId) {
    const wer = kachel.schritt.besatzung.map(sitzt => personName(sitzt.personId)).filter(Boolean)
    if (wer.length) zeilen.push(wer.join(', '))
  }
  const material = kachel.schritt.material
      .map(posten => materialName(posten.materialId)).filter(Boolean)
  if (material.length) zeilen.push(material.join(', '))
  if (kachel.schritt.notiz) zeilen.push(kachel.schritt.notiz)
  return zeilen
}
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-center gap-3 flex-wrap mb-3">
      <h2 class="abschnitt-titel">{{ t('ablauf.tagesplan') }}</h2>
      <select v-model="tag" class="field w-auto">
        <option v-for="wann in tage" :key="wann" :value="wann">{{ wann }}</option>
      </select>
      <span class="text-muted text-[13px]">{{ t('ablauf.tagesplanHinweis') }}</span>
    </div>

    <p v-if="!spalten.length" class="text-muted text-sm">{{ t('ablauf.keineSpalten') }}</p>

    <div v-else class="overflow-auto border border-rule rounded" style="max-height: 70vh">
      <div class="grid" :style="{gridTemplateColumns: `4rem repeat(${spalten.length}, minmax(9rem, 1fr))`}">
        <div class="sticky top-0 z-20 bg-surface border-b border-rule"></div>
        <div v-for="spalte in spalten" :key="spalte.schluessel"
             class="sticky top-0 z-20 bg-surface border-b border-l border-rule px-2 py-2">
          <span class="label block truncate" :title="spalte.name">
            <font-awesome-icon
              :icon="spalte.art === 'fahrzeug' ? 'fa-solid fa-truck' : 'fa-solid fa-users'"
              class="mr-1 text-muted"/>
            {{ spalte.name }}
          </span>
        </div>

        <div ref="gitter" class="relative" :style="{height: `${hoehe}px`}">
          <div v-for="wann in stunden" :key="wann"
               class="absolute right-2 -translate-y-1/2 tabular text-[13px] text-muted"
               :style="{top: `${oben(wann)}px`}">
            {{ beschriftung(wann) }}
          </div>
        </div>

        <div v-for="spalte in spalten" :key="`spur-${spalte.schluessel}`"
             class="relative border-l border-rule touch-none"
             :style="{height: `${hoehe}px`}"
             @pointerdown="fassen($event, 'neu', spalte)">
          <div v-for="wann in stunden" :key="wann"
               class="absolute inset-x-0 border-t border-hairline pointer-events-none"
               :style="{top: `${oben(wann)}px`}"></div>

          <div v-for="kachel in spalte.kacheln" :key="kachel.schritt.id"
               class="absolute inset-x-1 rounded border px-1.5 py-1 overflow-hidden text-[12px] leading-tight"
               :class="kachel.fremd
                 ? 'border-rule bg-raised text-muted cursor-pointer'
                 : 'border-band bg-surface cursor-grab'"
               :style="{top: `${oben(kachel.von)}px`,
                        height: `${Math.max(kachel.bis - kachel.von, RASTER) * PX_JE_MINUTE}px`}"
               @pointerdown.stop="kachel.fremd
                 ? oeffnen(kachel) : fassen($event, 'schieben', spalte, kachel)">
            <div v-if="kachel.da > kachel.von"
                 class="absolute inset-x-0 top-0 bg-band-track opacity-70 pointer-events-none"
                 :style="{height: `${(kachel.da - kachel.von) * PX_JE_MINUTE}px`}"></div>
            <div class="relative">
              <span class="tabular font-semibold">
                {{ beschriftung(kachel.da) }}–{{ beschriftung(kachel.bis) }}
              </span>
              <span v-for="(zeile, nummer) in stichworte(kachel)" :key="nummer" class="block truncate">
                {{ zeile }}
              </span>
            </div>
            <div v-if="!kachel.fremd"
                 class="absolute inset-x-0 bottom-0 h-2 cursor-ns-resize"
                 @pointerdown.stop="fassen($event, 'ende', spalte, kachel)"></div>
          </div>

          <div v-if="vorschau && vorschau.spalte.schluessel === spalte.schluessel"
               class="absolute inset-x-1 rounded border border-dashed border-focus bg-signal-soft pointer-events-none"
               :style="{top: `${oben(vorschau.von)}px`,
                        height: `${Math.max(vorschau.bis - vorschau.von, RASTER) * PX_JE_MINUTE}px`}"></div>
        </div>
      </div>
    </div>

    <SchrittFenster v-if="auswahl" :lauf="auswahl.lauf" :schritt="auswahl.schritt"
                    :name="auswahl.name" @schliessen="auswahl = null"/>
  </section>
</template>
