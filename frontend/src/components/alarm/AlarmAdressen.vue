<script setup lang="ts">
import AdresseFeld from '../base/AdresseFeld.vue'
import TextFeld from '../base/TextFeld.vue'
import {t} from '../../i18n'
import {zuPunkt, type Adresspunkt} from '../../api/adressen'
import {polarKoordinaten} from '../../scripts/polar'
import {arbeitsmappe, ortSichern} from '../../store/arbeitsmappe'
import type {Alarm} from '../../interfaces/Alarm'

const alarm = defineModel<Alarm>({required: true})

/** Zeigt eine Lage auf diesen Alarm, ist die Einsatzadresse die des Orts, an dem sie stattfindet. */
defineProps<{ ausPlan?: boolean }>()

/** The two addresses usually agree, so copying one over the other saves typing it twice. */
async function uebernehmen() {
  alarm.value.einsatzadresse = {...alarm.value.anfahrtsadresse}
  ortSichern(alarm.value.einsatzadresse)
  const ziel = await zuPunkt(alarm.value.einsatzadresse)
  if (ziel) await polarSetzen(ziel)
}

/**
 * Eine aufgelöste Einsatzadresse wird ein Ort im Katalog. Damit kann der Ablaufplan sie
 * auswählen, ohne dass sie ein zweites Mal getippt wird.
 */
function einsatzadresseGesetzt(ziel: Adresspunkt) {
  ortSichern(alarm.value.einsatzadresse)
  return polarSetzen(ziel)
}

/**
 * Where the Einsatzadresse lies seen from the station. Written as soon as both are known and
 * editable afterwards, the way the Trupp follows the Stärke.
 */
async function polarSetzen(ziel: Adresspunkt) {
  const wache = await zuPunkt(arbeitsmappe.kataloge.wache)
  if (wache) alarm.value.karte.polarKoordinaten = polarKoordinaten(wache, ziel)
}
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-center justify-between mb-3 gap-3 flex-wrap">
      <h2 class="abschnitt-titel mb-0">{{ t('abschnitt.adressen') }}</h2>
      <button v-if="!ausPlan" type="button" class="knopf knopf-klein" @click="uebernehmen">
        {{ t('adresse.uebernehmen') }}
      </button>
    </div>
    <div class="grid md:grid-cols-2 gap-5">
      <AdresseFeld v-model="alarm.anfahrtsadresse" :titel="t('adresse.anfahrt')"/>
      <AdresseFeld v-if="!ausPlan" v-model="alarm.einsatzadresse" :titel="t('adresse.einsatz')"
                   @aufgeloest="einsatzadresseGesetzt"/>
      <div v-else>
        <h3 class="label mb-2">{{ t('adresse.einsatz') }}</h3>
        <p class="text-muted text-sm">{{ t('ausPlan.adresse') }}</p>
      </div>
    </div>
  </section>

  <section class="abschnitt">
    <h2 class="abschnitt-titel">{{ t('abschnitt.karte') }}</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <TextFeld v-model="alarm.karte.kab" :label="t('feld.kab')"/>
      <TextFeld v-model="alarm.karte.fwPlan" :label="t('feld.fwPlan')"/>
      <TextFeld v-model="alarm.karte.ePlan" :label="t('feld.ePlan')"/>
      <TextFeld v-model="alarm.karte.polarKoordinaten" :label="t('feld.polarKoordinaten')"/>
    </div>
  </section>
</template>
