<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {ortsPunkte, plandaten, punkteLaden} from '../../store/planung'
import {bewegungstage, ereignisse, standorte} from '../../scripts/bewegungen'
import type {Standort} from '../../scripts/bewegungen'
import {mitte, utm33ZuWgs84} from '../../scripts/geo'
import type {Ortsmarke} from '../../scripts/geo'
import {alsMinuten, uhrzeit} from '../../scripts/zeit'

/**
 * Die Karte für den Ausführungstag: alle Orte, und darauf, wo jede Kette gerade ist. Der
 * Schieber verschiebt den dargestellten Zeitpunkt, „Jetzt“ hängt ihn an die Uhr — damit lässt
 * sich der Tag durchfahren, bevor er läuft, und mitverfolgen, während er läuft.
 */
const TAKT = 30000

const tage = computed(() => bewegungstage(plandaten()))
const tag = ref('')
const minute = ref(8 * 60)
const folgt = ref(false)
let uhr: ReturnType<typeof setInterval> | undefined

const zeitpunkt = computed(() =>
    `${tag.value}T${String(Math.floor(minute.value / 60)).padStart(2, '0')}:` +
    String(Math.floor(minute.value % 60)).padStart(2, '0'))

const fenster = computed(() => {
  const zeiten = arbeitsmappe.planung.laeufe
      .flatMap(lauf => lauf.schritte)
      .filter(schritt => schritt.von.slice(0, 10) === tag.value)
      .flatMap(schritt => [alsMinuten(schritt.von), alsMinuten(schritt.bis)])
      .filter((wert): wert is number => wert !== null)
  const mitternacht = alsMinuten(`${tag.value}T00:00`) ?? 0
  if (!zeiten.length) return {von: 6 * 60, bis: 22 * 60}
  return {
    von: Math.floor((Math.min(...zeiten) - mitternacht) / 60) * 60,
    bis: Math.ceil((Math.max(...zeiten) - mitternacht) / 60) * 60,
  }
})

const stand = computed(() => standorte(plandaten(), zeitpunkt.value))
const naechste = computed(() => ereignisse(plandaten(), zeitpunkt.value, 8))

function ortName(ortId: string): string {
  return arbeitsmappe.planung.orte.find(ort => ort.id === ortId)?.name ?? ''
}

function marke(ortId: string): Ortsmarke | null {
  const punkt = ortsPunkte[ortId]
  return punkt ? utm33ZuWgs84(punkt) : null
}

/** Wo eine Kette liegt: am Ort, oder anteilig auf der Luftlinie zwischen zwei Orten. */
function position(standort: Standort): Ortsmarke | null {
  if (!standort.unterwegs) return marke(standort.ortId)
  const von = marke(standort.unterwegs.vonOrtId)
  const nach = marke(standort.unterwegs.nachOrtId)
  if (!von || !nach) return von ?? nach
  const anteil = standort.unterwegs.anteil
  return {
    breite: von.breite + (nach.breite - von.breite) * anteil,
    laenge: von.laenge + (nach.laenge - von.laenge) * anteil,
  }
}

const behaelter = ref<HTMLElement>()
let karte: L.Map | undefined
let ortsschicht: L.LayerGroup | undefined
let bewegungsschicht: L.LayerGroup | undefined

function jetztSetzen() {
  const heute = new Date()
  const stunden = heute.getHours() * 60 + heute.getMinutes()
  if (tage.value.includes(heute.toISOString().slice(0, 10))) {
    tag.value = heute.toISOString().slice(0, 10)
  }
  minute.value = stunden
}

function folgenUmschalten() {
  folgt.value = !folgt.value
  if (folgt.value) jetztSetzen()
}

function ortePunkte() {
  if (!karte || !ortsschicht) return
  ortsschicht.clearLayers()
  const marken: Ortsmarke[] = []
  for (const ort of arbeitsmappe.planung.orte) {
    const punkt = marke(ort.id)
    if (!punkt) continue
    marken.push(punkt)
    L.circleMarker([punkt.breite, punkt.laenge], {
      radius: 8, color: '#e2483d', weight: 2, fillColor: '#e2483d', fillOpacity: 0.25,
    }).bindTooltip(ort.name || t('ablauf.ohneName'), {permanent: true, direction: 'right',
                                                     className: 'karte-ort'})
        .addTo(ortsschicht)
  }
  if (marken.length) {
    karte.fitBounds(L.latLngBounds(marken.map(m => [m.breite, m.laenge] as [number, number]))
        .pad(0.35))
  } else {
    const zentrum = mitte(marken)
    karte.setView([zentrum.breite, zentrum.laenge], 12)
  }
}

function bewegungZeichnen() {
  if (!bewegungsschicht) return
  bewegungsschicht.clearLayers()
  for (const standort of stand.value) {
    const punkt = position(standort)
    if (!punkt) continue
    const wer = standort.personen.filter(Boolean).join(', ')
    const beschriftung = [standort.name, wer && `(${wer})`].filter(Boolean).join(' ')
    L.marker([punkt.breite, punkt.laenge], {
      icon: L.divIcon({
        className: 'karte-kette',
        html: `<span class="${standort.unterwegs ? 'faehrt' : ''}">${beschriftung}</span>`,
        iconSize: [0, 0],
      }),
    }).addTo(bewegungsschicht)
    if (standort.unterwegs) {
      const von = marke(standort.unterwegs.vonOrtId)
      const nach = marke(standort.unterwegs.nachOrtId)
      if (von && nach) {
        L.polyline([[von.breite, von.laenge], [nach.breite, nach.laenge]], {
          color: '#e2483d', weight: 2, opacity: 0.5,
          dashArray: standort.unterwegs.mittel === 'fahrzeug' ? undefined : '5 5',
        }).addTo(bewegungsschicht)
      }
    }
  }
}

onMounted(async () => {
  tag.value = tage.value[0] ?? new Date().toISOString().slice(0, 10)
  minute.value = fenster.value.von
  await punkteLaden()
  if (!behaelter.value) return
  karte = L.map(behaelter.value, {attributionControl: true, zoomControl: true})
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© OpenStreetMap',
  }).addTo(karte)
  ortsschicht = L.layerGroup().addTo(karte)
  bewegungsschicht = L.layerGroup().addTo(karte)
  ortePunkte()
  bewegungZeichnen()
  uhr = setInterval(() => { if (folgt.value) jetztSetzen() }, TAKT)
})

onBeforeUnmount(() => {
  if (uhr) clearInterval(uhr)
  karte?.remove()
})

watch(() => arbeitsmappe.planung.orte.map(ort => Object.values(ort.adresse).join()).join('|'),
    async () => { await punkteLaden(); ortePunkte(); bewegungZeichnen() })
watch([stand, ortsPunkte], () => bewegungZeichnen())
watch(tage, liste => { if (!liste.includes(tag.value) && liste.length) tag.value = liste[0]! })
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-baseline gap-3 flex-wrap mb-3">
      <h2 class="abschnitt-titel mb-0">{{ t('ablauf.karte') }}</h2>
      <select v-if="tage.length > 1" v-model="tag" class="field w-auto">
        <option v-for="eintrag in tage" :key="eintrag" :value="eintrag">{{ eintrag }}</option>
      </select>
      <span v-else class="text-muted text-sm">{{ tag }}</span>
      <span class="grow"></span>
      <span class="tabular text-lg">{{ uhrzeit(zeitpunkt) }}</span>
      <button type="button" class="knopf knopf-klein" :class="folgt ? 'knopf-primaer' : ''"
              @click="folgenUmschalten">
        {{ t('ablauf.jetzt') }}
      </button>
    </div>

    <input v-model.number="minute" type="range" :min="fenster.von" :max="fenster.bis" step="5"
           class="w-full mb-3" @input="folgt = false"/>

    <div class="grid lg:grid-cols-[1fr_280px] gap-4 items-start">
      <div ref="behaelter" class="h-[60vh] min-h-80 rounded border border-rule"></div>

      <div class="grid gap-2">
        <h3 class="label">{{ t('ablauf.naechste') }}</h3>
        <p v-if="!naechste.length" class="text-muted text-sm">{{ t('ablauf.nichtsMehr') }}</p>
        <div v-for="(ereignis, nummer) in naechste" :key="nummer"
             class="border-l-2 border-rule pl-3 py-1">
          <div class="flex items-baseline gap-2">
            <span class="tabular text-sm">{{ uhrzeit(ereignis.zeitpunkt) }}</span>
            <span class="text-muted text-[13px]">{{ t('ablauf.inMinuten', {n: ereignis.in}) }}</span>
          </div>
          <div class="text-sm">
            {{ ereignis.name }}
            <span class="text-muted">
              {{ ereignis.art === 'abfahrt' ? t('ablauf.faehrtNach') : t('ablauf.istAn') }}
              {{ ortName(ereignis.ortId) || t('ablauf.ohneName') }}
            </span>
          </div>
          <div v-if="ereignis.lage" class="text-[13px] text-muted">{{ ereignis.lage }}</div>
        </div>
      </div>
    </div>

    <p class="text-muted text-[13px] mt-2">{{ t('ablauf.karteHinweis') }}</p>
  </section>
</template>

<style>
.karte-ort {
  background: #101114;
  color: #f5f5f5;
  border: 1px solid rgba(245, 245, 245, 0.35);
  box-shadow: none;
  font-weight: 600;
  padding: 1px 6px;
}

.karte-ort::before {
  display: none;
}

.karte-kette span {
  display: inline-block;
  white-space: nowrap;
  transform: translate(-50%, -160%);
  padding: 1px 6px;
  border-radius: 3px;
  background: #101114;
  color: #f5f5f5;
  border: 1px solid #e2483d;
  font-size: 12px;
}

.karte-kette span.faehrt {
  border-style: dashed;
}
</style>
