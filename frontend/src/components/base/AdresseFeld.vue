<script setup lang="ts">
import {computed, defineAsyncComponent, onBeforeUnmount, ref, watch} from 'vue'
import AuswahlFeld from './AuswahlFeld.vue'
import TextFeld from './TextFeld.vue'
import {t} from '../../i18n'
import {adresspunkt, suchen, type Adresspunkt, type Adressvorschlag} from '../../api/adressen'
import type {Adresse} from '../../interfaces/Alarm'

defineProps<{ titel: string }>()
const emit = defineEmits<{ aufgeloest: [Adresspunkt] }>()
const adresse = defineModel<Adresse>({required: true})

/** Leaflet bringt seine eigene Last mit und wird erst geholt, wenn jemand die Karte aufmacht. */
const PunktFenster = defineAsyncComponent(() => import('./PunktFenster.vue'))
const kartewahl = ref(false)

/** Ein auf der Karte gesetzter Punkt gilt vor der Straße. */
function punktSetzen(wert: string) {
  adresse.value.koordinaten = wert
  kartewahl.value = false
}

const treffer = ref<Adressvorschlag[]>([])
const vorschlaege = computed(() => treffer.value.map(eintrag => eintrag.beschriftung))

let zaehler = 0
let warten: number | undefined

/**
 * Suggestions follow the typing, but the answers do not come back in the order they were asked
 * for. Each request carries a number and a late answer to an older one is dropped, or a slow
 * reply for "mark" would overwrite the list for "marksburg".
 */
function suggerieren(wert: string) {
    window.clearTimeout(warten)
    warten = window.setTimeout(async () => {
        const lauf = ++zaehler
        const gefunden = await suchen(wert)
        if (lauf !== zaehler) return
        treffer.value = gefunden
    }, 200)
}

/**
 * A picked suggestion carries the whole address, so "Archenholdstr 21" typed into this one field
 * settles street, number, postcode and Ortsteil together. Anything typed and left alone falls
 * back to looking up whatever the separate fields hold.
 */
function uebernehmen() {
    const gewaehlt = treffer.value.find(eintrag => eintrag.beschriftung === adresse.value.strasse)
    if (!gewaehlt) {
        aufloesen()
        return
    }
    adresse.value.strasse = gewaehlt.strasse
    adresse.value.plz = gewaehlt.plz
    adresse.value.ort = gewaehlt.ort
    if (gewaehlt.hnr) adresse.value.hnr = gewaehlt.hnr
    if (gewaehlt.ostwert !== null && gewaehlt.nordwert !== null) {
        emit('aufgeloest', gewaehlt as Adresspunkt)
    } else {
        aufloesen()
    }
}

async function aufloesen() {
    const punkt = await adresspunkt(adresse.value.strasse, adresse.value.hnr, adresse.value.plz)
    if (!punkt) return
    adresse.value.plz = punkt.plz
    adresse.value.ort = punkt.ort
    emit('aufgeloest', punkt)
}

watch(() => adresse.value.strasse, suggerieren)
onBeforeUnmount(() => window.clearTimeout(warten))
</script>

<template>
  <div>
    <div class="label mb-2">{{ titel }}</div>
    <div class="grid grid-cols-3 gap-3">
      <AuswahlFeld v-model="adresse.strasse" :label="t('feld.strasse')" :vorschlaege="vorschlaege"
                   :platzhalter="t('adresse.platzhalter')" breit vorgefiltert
                   @change="uebernehmen"/>
      <TextFeld v-model="adresse.hnr" :label="t('feld.hnr')" @change="aufloesen"/>
      <TextFeld v-model="adresse.objekt" :label="t('feld.objekt')" breit/>
      <TextFeld v-model="adresse.plz" :label="t('feld.plz')" @change="aufloesen"/>
      <TextFeld v-model="adresse.ort" :label="t('feld.ort')" breit/>
    </div>

    <div class="flex items-center gap-2 flex-wrap mt-2">
      <button type="button" class="knopf knopf-klein" @click="kartewahl = true">
        <font-awesome-icon icon="fa-solid fa-location-dot"/>
        {{ adresse.koordinaten ? t('adresse.punktAendern') : t('adresse.punktWaehlen') }}
      </button>
      <span v-if="adresse.koordinaten" class="tabular text-[13px] text-muted"
            :title="t('adresse.punktGilt')">
        {{ adresse.koordinaten }}
      </span>
    </div>

    <PunktFenster v-if="kartewahl" :adresse="adresse" @setzen="punktSetzen"
                  @schliessen="kartewahl = false"/>
  </div>
</template>
