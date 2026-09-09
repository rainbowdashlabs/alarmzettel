<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {alleOrte, ortsPunkte, plandaten, punkteLaden} from '../../store/planung'
import {bewegungstage, ereignisse, materialstand, standorte} from '../../scripts/bewegungen'
import type {Standort} from '../../scripts/bewegungen'
import {mitte, utm33ZuWgs84} from '../../scripts/geo'
import type {Ortsmarke} from '../../scripts/geo'
import {alsMinuten, uhrzeit} from '../../scripts/zeit'

/**
 * Die Karte für den Ausführungstag: alle Orte, und darauf, wo jede Kette gerade ist. Der
 * Schieber verschiebt den dargestellten Zeitpunkt minutenweise, „Jetzt“ hängt ihn an die Uhr —
 * damit lässt sich der Tag durchfahren, bevor er läuft, und mitverfolgen, während er läuft.
 *
 * Ob die Karte der Uhr folgt, merkt sich der Browser: am Ausführungstag will man sie aufschlagen
 * und die Lage sehen, nicht erst einen Knopf suchen.
 */
const TAKT = 10000

const SPEICHER = 'alarmplaner_karte_folgt'

const tage = computed(() => bewegungstage(plandaten()))
const tag = ref('')
const minute = ref(8 * 60)
const folgt = ref(localStorage.getItem(SPEICHER) === 'ja')
let uhr: ReturnType<typeof setInterval> | undefined

/** Der heutige Tag, wie die Uhr an der Wand ihn zählt — nicht der, den UTC gerade hat. */
function heutigerTag(): string {
  const jetzt = new Date()
  return `${jetzt.getFullYear()}-${String(jetzt.getMonth() + 1).padStart(2, '0')}-` +
      String(jetzt.getDate()).padStart(2, '0')
}

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
  // Der gezeigte Zeitpunkt gehört immer ins Fenster: sonst stünde der Schieber am Anschlag,
  // während die Karte die Uhrzeit zeigt, und beide sagten Verschiedenes.
  const gezeigt = minute.value
  if (!zeiten.length) return {von: Math.min(6 * 60, gezeigt), bis: Math.max(22 * 60, gezeigt)}
  return {
    von: Math.min(Math.floor((Math.min(...zeiten) - mitternacht) / 60) * 60, gezeigt),
    bis: Math.max(Math.ceil((Math.max(...zeiten) - mitternacht) / 60) * 60, gezeigt),
  }
})

const stand = computed(() => standorte(plandaten(), zeitpunkt.value))
const naechste = computed(() => ereignisse(plandaten(), zeitpunkt.value, 8))
const material = computed(() => materialstand(plandaten(), zeitpunkt.value))

function ortName(ortId: string): string {
  return alleOrte().find(ort => ort.id === ortId)?.name ?? ''
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
  if (tage.value.includes(heutigerTag())) tag.value = heutigerTag()
  minute.value = heute.getHours() * 60 + heute.getMinutes()
}

/** Wer selbst am Schieber zieht, will nicht, dass die Uhr ihn gleich wieder wegzieht. */
function folgenBeenden() {
  if (!folgt.value) return
  folgt.value = false
  localStorage.setItem(SPEICHER, 'nein')
}

function folgenUmschalten() {
  folgt.value = !folgt.value
  localStorage.setItem(SPEICHER, folgt.value ? 'ja' : 'nein')
  if (folgt.value) jetztSetzen()
}

function ortePunkte() {
  if (!karte || !ortsschicht) return
  ortsschicht.clearLayers()
  const marken: Ortsmarke[] = []
  for (const ort of alleOrte()) {
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
  tag.value = tage.value[0] ?? heutigerTag()
  minute.value = fenster.value.von
  if (folgt.value) jetztSetzen()
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

watch(() => alleOrte().map(ort => Object.values(ort.adresse).join()).join('|'),
    async () => { await punkteLaden(); ortePunkte(); bewegungZeichnen() })
watch([stand, ortsPunkte], () => bewegungZeichnen())
watch(tage, liste => { if (!liste.includes(tag.value) && liste.length) tag.value = liste[0]! })
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-baseline gap-3 flex-wrap mb-3">
      <h2 class="abschnitt-titel">{{ t('ablauf.karte') }}</h2>
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

    <input v-model.number="minute" type="range" :min="fenster.von" :max="fenster.bis" step="1"
           class="w-full mb-3" @input="folgenBeenden"/>

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

        <template v-if="material.length">
          <h3 class="label mt-3">{{ t('ablauf.material') }}</h3>
          <div v-for="stand in material" :key="stand.materialId" class="text-sm">
            <font-awesome-icon icon="fa-solid fa-box" class="text-muted mr-1"/>
            <span v-if="stand.anzahl > 1" class="tabular">{{ t('ablauf.materialMenge', {n: stand.anzahl}) }}</span>
            {{ stand.name }}
            <span class="text-muted">
              {{ stand.unterwegs
                ? t('ablauf.materialUnterwegs', {womit: stand.traeger,
                                                 wohin: ortName(stand.unterwegs.nachOrtId)})
                : t('ablauf.materialAn', {wo: ortName(stand.ortId)}) }}
            </span>
          </div>
        </template>
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
