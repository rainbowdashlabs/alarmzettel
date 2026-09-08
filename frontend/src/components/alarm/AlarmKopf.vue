<script setup lang="ts">
import AuswahlFeld from '../base/AuswahlFeld.vue'
import JaNeinFeld from '../base/JaNeinFeld.vue'
import TextFeld from '../base/TextFeld.vue'
import TextBereich from '../base/TextBereich.vue'
import {t} from '../../i18n'
import {stichwortVorschlaege} from '../../store/arbeitsmappe'
import type {Alarm} from '../../interfaces/Alarm'

const alarm = defineModel<Alarm>({required: true})
</script>

<template>
  <section class="abschnitt">
    <h2 class="abschnitt-titel">{{ t('abschnitt.kopf') }}</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <TextFeld v-model="alarm.einsatzNr" :label="t('feld.einsatzNr')"/>
      <TextFeld v-model="alarm.aPlatz" :label="t('feld.aPlatz')"/>
      <TextFeld v-model="alarm.behoerde" :label="t('feld.behoerde')"/>
      <TextFeld v-model="alarm.titel" :label="t('feld.titel')"/>
      <TextFeld v-model="alarm.einsatzDatum" :label="t('feld.einsatzDatum')"/>
      <TextFeld v-model="alarm.einsatzZeit" :label="t('feld.einsatzZeit')"/>
      <TextFeld v-model="alarm.meldungDatum" :label="t('feld.meldungDatum')"/>
      <TextFeld v-model="alarm.meldungZeit" :label="t('feld.meldungZeit')"/>
      <JaNeinFeld v-model="alarm.polizei" :label="t('feld.polizei')"/>
      <JaNeinFeld v-model="alarm.sonderrechte" :label="t('feld.sonderrechte')"/>
      <TextFeld v-model="alarm.arbeitsgruppe" :label="t('feld.arbeitsgruppe')"/>
      <TextFeld v-model="alarm.wachalarmNr" :label="t('feld.wachalarmNr')"/>
    </div>
  </section>

  <section class="abschnitt">
    <h2 class="abschnitt-titel">{{ t('abschnitt.stichwort') }}</h2>
    <div class="grid gap-3">
      <AuswahlFeld v-model="alarm.stichwort" :label="t('feld.stichwort')"
                   :vorschlaege="stichwortVorschlaege()"/>
      <TextBereich v-model="alarm.kurzinfo" :label="t('feld.kurzinfo')" :zeilen="2"/>
    </div>
  </section>
</template>
