<script setup lang="ts">
import TextFeld from '../base/TextFeld.vue'
import TextBereich from '../base/TextBereich.vue'
import {t} from '../../i18n'
import {festnetznummer, mobilnummer, zufallsname} from '../../scripts/generator'
import type {Alarm} from '../../interfaces/Alarm'

const alarm = defineModel<Alarm>({required: true})

/** These sheets are written for practice, so the personal details are made up, not typed. */
function neuErzeugen() {
  alarm.value.meldungsquelle = festnetznummer()
  alarm.value.rueckrufnummer = mobilnummer()
  alarm.value.anrufer = zufallsname()
}
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
      <h2 class="abschnitt-titel">{{ t('abschnitt.beteiligte') }}</h2>
      <button type="button" class="knopf knopf-klein" :title="t('feld.erzeugenHinweis')"
              @click="neuErzeugen">
        <font-awesome-icon icon="fa-solid fa-rotate"/>
        {{ t('feld.erzeugen') }}
      </button>
    </div>
    <div class="grid md:grid-cols-2 gap-3">
      <TextFeld v-model="alarm.meldungsquelle" :label="t('feld.meldungsquelle')"/>
      <TextFeld v-model="alarm.rueckrufnummer" :label="t('feld.rueckrufnummer')"/>
      <TextFeld v-model="alarm.anrufer" :label="t('feld.anrufer')"/>
      <TextFeld v-model="alarm.betroffener" :label="t('feld.betroffener')"/>
      <TextFeld v-model="alarm.meldender" :label="t('feld.meldender')"/>
    </div>
    <div class="mt-3">
      <TextBereich v-model="alarm.wasIstPassiert" :label="t('feld.wasIstPassiert')" :zeilen="2"/>
    </div>
  </section>
</template>
