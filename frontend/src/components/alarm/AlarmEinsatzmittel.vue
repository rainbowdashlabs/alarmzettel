<script setup lang="ts">
import AuswahlFeld from '../base/AuswahlFeld.vue'
import TextFeld from '../base/TextFeld.vue'
import {t} from '../../i18n'
import {
  fahrzeugSichern,
  fahrzeugvorlage,
  funkrufnameVorschlaege,
  statusVorschlaege,
  truppVorschlaege,
} from '../../store/arbeitsmappe'
import {fahrzeugwerte} from '../../scripts/katalog'
import {leereGruppe, leeresFahrzeug, naechste, type Alarm, type Fahrzeug} from '../../interfaces/Alarm'

const alarm = defineModel<Alarm>({required: true})

/** Zeigt eine Lage auf diesen Alarm, kommt das Aufgebot aus dem Plan. */
defineProps<{ ausPlan?: boolean }>()

function gruppeHinzufuegen() {
  alarm.value.einsatzmittel.push(leereGruppe(naechste(alarm.value.einsatzmittel)))
}

function gruppeEntfernen(index: number) {
  alarm.value.einsatzmittel.splice(index, 1)
}

function fahrzeugHinzufuegen(index: number) {
  const gruppe = alarm.value.einsatzmittel[index]
  gruppe?.fahrzeuge.push(leeresFahrzeug(naechste(gruppe.fahrzeuge)))
}

function fahrzeugEntfernen(gruppe: number, fahrzeug: number) {
  alarm.value.einsatzmittel[gruppe]?.fahrzeuge.splice(fahrzeug, 1)
}

/**
 * What this vehicle prints, catalogue included — shown as the placeholder of every field the
 * Alarm leaves empty, so the sheet holds no value the editor does not show.
 */
function werte(fahrzeug: Fahrzeug) {
  return fahrzeugwerte(fahrzeug, fahrzeugvorlage(fahrzeug))
}

/**
 * A different vehicle answers for itself. Anything overridden for the one before it would
 * otherwise stay behind and quietly describe the wrong wagen.
 *
 * A Funkrufname is linked to its catalogue entry by id rather than by the name, so renaming the
 * vehicle later reaches this row too. One written for the first time joins the catalogue, which
 * is also where its Stärke, EZP and Status will be filled in once.
 */
function vorlageUebernehmen(fahrzeug: Fahrzeug) {
  fahrzeug.vorlageId = fahrzeugSichern(fahrzeug.funkrufname)
  fahrzeug.ezp = ''
  fahrzeug.status = ''
  fahrzeug.staerke = ''
  fahrzeug.trupp = ''
}

/**
 * The sheet is addressed to a single vehicle, so choosing one clears the rest. Choosing the
 * vehicle that is already marked clears it again, leaving the Alarm with none highlighted.
 */
function alarmFuerWaehlen(gruppe: number, fahrzeug: number) {
  const gewaehlt = alarm.value.einsatzmittel[gruppe]?.fahrzeuge[fahrzeug]
  if (!gewaehlt) return
  const vorher = gewaehlt.alarmFuer
  for (const eintrag of alarm.value.einsatzmittel) {
    for (const wagen of eintrag.fahrzeuge) wagen.alarmFuer = false
  }
  gewaehlt.alarmFuer = !vorher
}
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
      <h2 class="abschnitt-titel mb-0">{{ t('abschnitt.einsatzmittel') }}</h2>
      <button type="button" class="knopf knopf-klein" @click="gruppeHinzufuegen">
        <font-awesome-icon icon="fa-solid fa-plus"/>
        {{ t('einsatzmittel.gruppeNeu') }}
      </button>
    </div>

    <p v-if="ausPlan" class="text-signal-ink text-[13px] mb-3">{{ t('ausPlan.aufgebot') }}</p>
    <p class="text-muted text-[13px] mb-3">{{ t('einsatzmittel.alarmFuerHinweis') }}</p>
    <p class="text-muted text-[13px] mb-3">{{ t('einsatzmittel.haHinweis') }}</p>
    <p class="text-muted text-[13px] mb-3">{{ t('einsatzmittel.katalogHinweis') }}</p>

    <div class="grid gap-4">
      <div v-for="(gruppe, gruppeIndex) in alarm.einsatzmittel" :key="gruppeIndex"
           class="border border-rule rounded p-3 bg-page">
        <div class="grid md:grid-cols-[1fr_auto] gap-3 items-end mb-3">
          <div class="grid md:grid-cols-3 gap-3">
            <TextFeld v-model="gruppe.gruppe" :label="t('feld.gruppe')"/>
          </div>
          <button type="button" class="knopf knopf-klein knopf-gefahr"
                  :disabled="alarm.einsatzmittel.length === 1"
                  @click="gruppeEntfernen(gruppeIndex)">
            <font-awesome-icon icon="fa-solid fa-trash"/>
            {{ t('einsatzmittel.gruppeEntfernen') }}
          </button>
        </div>

        <p v-if="!gruppe.fahrzeuge.length" class="text-muted text-sm mb-2">
          {{ t('einsatzmittel.leer') }}
        </p>

        <div class="grid gap-2">
          <div v-for="(fahrzeug, fahrzeugIndex) in gruppe.fahrzeuge" :key="fahrzeugIndex"
               class="grid md:grid-cols-[1fr_auto] gap-2 items-end">
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
              <AuswahlFeld v-model="fahrzeug.funkrufname" :label="t('feld.funkrufname')"
                           :vorschlaege="funkrufnameVorschlaege()"
                           @change="vorlageUebernehmen(fahrzeug)"/>
              <TextFeld v-model="fahrzeug.ezp" :label="t('feld.ezp')"
                        :platzhalter="werte(fahrzeug).ezp"/>
              <AuswahlFeld v-model="fahrzeug.status" :label="t('feld.status')"
                           :vorschlaege="statusVorschlaege()"
                           :platzhalter="werte(fahrzeug).status"/>
              <TextFeld v-model="fahrzeug.staerke" :label="t('feld.staerke')"
                        :platzhalter="werte(fahrzeug).staerke"/>
              <AuswahlFeld v-model="fahrzeug.trupp" :label="t('feld.trupp')"
                           :vorschlaege="truppVorschlaege()"
                           :platzhalter="werte(fahrzeug).trupp"/>
              <TextFeld v-model="fahrzeug.hinweis" :label="t('feld.fahrzeugHinweis')"/>
            </div>
            <div class="flex gap-2">
              <button type="button" class="knopf knopf-klein"
                      :class="fahrzeug.alarmFuer ? 'knopf-primaer' : ''"
                      :title="t('einsatzmittel.alarmFuer')"
                      @click="alarmFuerWaehlen(gruppeIndex, fahrzeugIndex)">
                <font-awesome-icon :icon="fahrzeug.alarmFuer ? 'fa-solid fa-circle-check' : 'fa-regular fa-circle'"/>
                {{ t('einsatzmittel.alarmFuerKurz') }}
              </button>
              <button type="button" class="knopf knopf-klein knopf-gefahr"
                      :title="t('einsatzmittel.fahrzeugEntfernen')"
                      @click="fahrzeugEntfernen(gruppeIndex, fahrzeugIndex)">
                <font-awesome-icon icon="fa-solid fa-xmark"/>
              </button>
            </div>
          </div>
        </div>

        <button type="button" class="knopf knopf-klein mt-3" @click="fahrzeugHinzufuegen(gruppeIndex)">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('einsatzmittel.fahrzeugNeu') }}
        </button>
      </div>
    </div>
  </section>
</template>
