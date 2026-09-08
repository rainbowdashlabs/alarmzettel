<script setup lang="ts">
import AdresseFeld from '../base/AdresseFeld.vue'
import TextFeld from '../base/TextFeld.vue'
import {t} from '../../i18n'
import type {Alarm} from '../../interfaces/Alarm'

const alarm = defineModel<Alarm>({required: true})

/** The two addresses usually agree, so copying one over the other saves typing it twice. */
function uebernehmen() {
  alarm.value.einsatzadresse = {...alarm.value.anfahrtsadresse}
}
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-center justify-between mb-3 gap-3 flex-wrap">
      <h2 class="abschnitt-titel mb-0">{{ t('abschnitt.adressen') }}</h2>
      <button type="button" class="knopf knopf-klein" @click="uebernehmen">
        {{ t('adresse.uebernehmen') }}
      </button>
    </div>
    <div class="grid md:grid-cols-2 gap-5">
      <AdresseFeld v-model="alarm.anfahrtsadresse" :titel="t('adresse.anfahrt')"/>
      <AdresseFeld v-model="alarm.einsatzadresse" :titel="t('adresse.einsatz')"/>
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
