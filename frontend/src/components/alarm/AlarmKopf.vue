<script setup lang="ts">
import AuswahlFeld from '../base/AuswahlFeld.vue'
import JaNeinFeld from '../base/JaNeinFeld.vue'
import TextFeld from '../base/TextFeld.vue'
import TextBereich from '../base/TextBereich.vue'
import {t} from '../../i18n'
import {stichwortSichern, stichwortVorschlaege} from '../../store/arbeitsmappe'
import type {Alarm} from '../../interfaces/Alarm'

const alarm = defineModel<Alarm>({required: true})

/**
 * The Meldung follows the Einsatz. The two are minutes apart on a real call, but on a sheet
 * written for an exercise they are the same time far more often than not, and typing it twice is
 * work for nothing. Correcting the Meldungszeit afterwards stands until the Einsatzzeit is
 * touched again.
 */
function meldungszeitFolgen() {
  alarm.value.meldungZeit = alarm.value.einsatzZeit
}

/**
 * A Stichwort is linked to its catalogue entry by id rather than by its text, so correcting the
 * catalogue later reaches this Alarm. One written for the first time joins the catalogue, which
 * is what gives it an entry to be linked to.
 */
function stichwortGewaehlt() {
  alarm.value.stichwortId = stichwortSichern(alarm.value.stichwort)
}
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
      <TextFeld v-model="alarm.einsatzZeit" :label="t('feld.einsatzZeit')"
                @change="meldungszeitFolgen"/>
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
                   :vorschlaege="stichwortVorschlaege()" @change="stichwortGewaehlt"/>
      <TextBereich v-model="alarm.kurzinfo" :label="t('feld.kurzinfo')" :zeilen="2"/>
    </div>
  </section>
</template>
