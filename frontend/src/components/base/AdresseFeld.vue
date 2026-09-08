<script setup lang="ts">
import {onBeforeUnmount, ref, watch} from 'vue'
import AuswahlFeld from './AuswahlFeld.vue'
import TextFeld from './TextFeld.vue'
import {t} from '../../i18n'
import {adresspunkt, strassen, type Adresspunkt, type Strassentreffer} from '../../api/adressen'
import type {Adresse} from '../../interfaces/Alarm'

defineProps<{ titel: string }>()
const emit = defineEmits<{ aufgeloest: [Adresspunkt] }>()
const adresse = defineModel<Adresse>({required: true})

const vorschlaege = ref<string[]>([])
const treffer = ref<Strassentreffer[]>([])

let zaehler = 0
let warten: number | undefined

/**
 * Suggestions follow the typing, but the answers do not come back in the order they were asked
 * for. Each request carries a number and a late answer to an older one is dropped, or a slow
 * reply for "mark" would overwrite the list for "marksburg".
 */
function suchen(wert: string) {
    window.clearTimeout(warten)
    warten = window.setTimeout(async () => {
        const lauf = ++zaehler
        const gefunden = await strassen(wert)
        if (lauf !== zaehler) return
        treffer.value = gefunden
        vorschlaege.value = [...new Set(gefunden.map(eintrag => eintrag.strasse))]
    }, 200)
}

/**
 * A street that runs through one postcode only settles it there and then; one crossing several
 * waits for the house number to say which.
 */
function strasseGewaehlt() {
    const passend = treffer.value.filter(eintrag => eintrag.strasse === adresse.value.strasse)
    if (passend.length === 1 && passend[0]) {
        adresse.value.plz = passend[0].plz
        adresse.value.ort = passend[0].ort
    }
    aufloesen()
}

async function aufloesen() {
    const punkt = await adresspunkt(adresse.value.strasse, adresse.value.hnr, adresse.value.plz)
    if (!punkt) return
    adresse.value.plz = punkt.plz
    adresse.value.ort = punkt.ort
    emit('aufgeloest', punkt)
}

watch(() => adresse.value.strasse, suchen)
onBeforeUnmount(() => window.clearTimeout(warten))
</script>

<template>
  <div>
    <div class="label mb-2">{{ titel }}</div>
    <div class="grid grid-cols-3 gap-3">
      <AuswahlFeld v-model="adresse.strasse" :label="t('feld.strasse')" :vorschlaege="vorschlaege"
                   breit @change="strasseGewaehlt"/>
      <TextFeld v-model="adresse.hnr" :label="t('feld.hnr')" @change="aufloesen"/>
      <TextFeld v-model="adresse.objekt" :label="t('feld.objekt')" breit/>
      <TextFeld v-model="adresse.plz" :label="t('feld.plz')" @change="aufloesen"/>
      <TextFeld v-model="adresse.ort" :label="t('feld.ort')" breit/>
    </div>
  </div>
</template>
