<script setup lang="ts">
import {onBeforeUnmount, onMounted, ref} from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {t} from '../../i18n'
import {markeAlsText, markeAusText, mitte, utm33ZuWgs84} from '../../scripts/geo'
import type {Ortsmarke} from '../../scripts/geo'
import {zuPunkt} from '../../api/adressen'
import type {Adresse} from '../../interfaces/Alarm'

/**
 * Einen Punkt auf der Karte setzen. Für alles, was keine Hausnummer hat: den Hof hinter dem
 * Haus, die Wiese, den Treffpunkt am Waldrand. Was hier gesetzt wird, gilt vor der Straße.
 *
 * Die Karte öffnet dort, wo etwas schon steht — beim gesetzten Punkt, sonst bei der
 * nachgeschlagenen Adresse, sonst über Berlin.
 */
const {adresse} = defineProps<{ adresse: Adresse }>()
const meldet = defineEmits<{ setzen: [wert: string], schliessen: [] }>()

const behaelter = ref<HTMLElement>()
const gewaehlt = ref<Ortsmarke | null>(markeAusText(adresse.koordinaten ?? ''))
let karte: L.Map | undefined
let marke: L.Marker | undefined

function setzen(punkt: Ortsmarke) {
  gewaehlt.value = punkt
  const stelle: L.LatLngExpression = [punkt.breite, punkt.laenge]
  if (marke) marke.setLatLng(stelle)
  else if (karte) {
    marke = L.marker(stelle, {draggable: true}).addTo(karte)
    marke.on('dragend', () => {
      const wo = marke!.getLatLng()
      gewaehlt.value = {breite: wo.lat, laenge: wo.lng}
    })
  }
}

onMounted(async () => {
  const aus = gewaehlt.value ?? await gesucht()
  if (!behaelter.value) return
  const zentrum = aus ?? mitte([])
  karte = L.map(behaelter.value).setView([zentrum.breite, zentrum.laenge], aus ? 17 : 11)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© OpenStreetMap',
  }).addTo(karte)
  if (gewaehlt.value) setzen(gewaehlt.value)
  karte.on('click', (ereignis: L.LeafletMouseEvent) =>
      setzen({breite: ereignis.latlng.lat, laenge: ereignis.latlng.lng}))
})

/** Wo die Adresse liegt, soweit der Dienst sie kennt — nur als Startpunkt der Karte. */
async function gesucht(): Promise<Ortsmarke | null> {
  const punkt = await zuPunkt({...adresse, koordinaten: ''})
  return punkt ? utm33ZuWgs84(punkt) : null
}

onBeforeUnmount(() => karte?.remove())
</script>

<template>
  <div class="fixed inset-0 z-50 bg-black/55 flex items-start justify-center p-4 overflow-auto"
       @click.self="meldet('schliessen')">
    <div class="abschnitt w-full max-w-3xl my-6 grid gap-3">
      <div class="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 class="abschnitt-titel">{{ t('adresse.punktTitel') }}</h2>
          <p class="text-muted text-sm mt-1">{{ t('adresse.punktHinweis') }}</p>
        </div>
        <button type="button" class="knopf knopf-klein" @click="meldet('schliessen')">
          <font-awesome-icon icon="fa-solid fa-xmark"/>
          {{ t('aktion.abbrechen') }}
        </button>
      </div>

      <div ref="behaelter" class="h-[55vh] min-h-72 rounded border border-rule"></div>

      <div class="flex items-center gap-3 flex-wrap">
        <span class="tabular text-sm">
          {{ gewaehlt ? markeAlsText(gewaehlt) : t('adresse.punktKeiner') }}
        </span>
        <span class="grow"></span>
        <button v-if="adresse.koordinaten" type="button" class="knopf knopf-klein knopf-gefahr"
                @click="meldet('setzen', '')">
          <font-awesome-icon icon="fa-solid fa-trash"/>
          {{ t('adresse.punktLoeschen') }}
        </button>
        <button type="button" class="knopf knopf-klein knopf-primaer" :disabled="!gewaehlt"
                @click="meldet('setzen', gewaehlt ? markeAlsText(gewaehlt) : '')">
          <font-awesome-icon icon="fa-solid fa-check"/>
          {{ t('adresse.punktSetzen') }}
        </button>
      </div>
    </div>
  </div>
</template>
