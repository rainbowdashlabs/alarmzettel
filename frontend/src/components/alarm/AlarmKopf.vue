<script setup lang="ts">
import AuswahlFeld from '../base/AuswahlFeld.vue'
import JaNeinFeld from '../base/JaNeinFeld.vue'
import TextFeld from '../base/TextFeld.vue'
import ZeitpunktFeld from '../base/ZeitpunktFeld.vue'
import TextBereich from '../base/TextBereich.vue'
import {t} from '../../i18n'
import {stichwortSichern, stichwortVorschlaege} from '../../store/arbeitsmappe'
import type {Alarm} from '../../interfaces/Alarm'

const alarm = defineModel<Alarm>({required: true})

/**
 * Zeigt eine Lage auf diesen Alarm, kommen die Zeiten aus dem Ablaufplan. Dann stehen hier die
 * Werte, die gedruckt werden, und nicht die eingetippten, die es nicht aufs Blatt schaffen.
 */
const {zeiten} = defineProps<{ zeiten?: Record<string, string> }>()

const ZEITPUNKTE = ['einsatz', 'meldung'] as const

/**
 * The Meldung follows the Einsatz. The two are minutes apart on a real call, but on a sheet
 * written for an exercise they are the same time far more often than not, and typing it twice is
 * work for nothing. Correcting the Meldung afterwards stands until the Einsatz is touched again.
 */
function meldungFolgt() {
  alarm.value.meldungDatum = alarm.value.einsatzDatum
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
      <div v-if="zeiten?.einsatzNr">
        <label class="feld-label">{{ t('feld.einsatzNr') }}</label>
        <input type="text" class="field" disabled :value="zeiten.einsatzNr"/>
      </div>
      <TextFeld v-else v-model="alarm.einsatzNr" :label="t('feld.einsatzNr')"/>
      <TextFeld v-model="alarm.aPlatz" :label="t('feld.aPlatz')"/>
      <TextFeld v-model="alarm.behoerde" :label="t('feld.behoerde')"/>
      <TextFeld v-model="alarm.titel" :label="t('feld.titel')"/>
      <template v-if="zeiten">
        <div v-for="name in ZEITPUNKTE" :key="name">
          <label class="feld-label">{{ t(`feld.${name}`) }}</label>
          <input type="text" class="field" disabled
                 :value="`${zeiten[`${name}Datum`]} ${zeiten[`${name}Zeit`]}`.trim()"/>
        </div>
      </template>
      <template v-else>
        <ZeitpunktFeld v-model:datum="alarm.einsatzDatum" v-model:zeit="alarm.einsatzZeit"
                       :label="t('feld.einsatz')" @change="meldungFolgt"/>
        <ZeitpunktFeld v-model:datum="alarm.meldungDatum" v-model:zeit="alarm.meldungZeit"
                       :label="t('feld.meldung')"/>
      </template>
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
