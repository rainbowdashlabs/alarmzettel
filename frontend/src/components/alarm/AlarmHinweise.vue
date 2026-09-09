<script setup lang="ts">
import {ref} from 'vue'
import SnaDialog from '../sna/SnaDialog.vue'
import {t} from '../../i18n'
import {neuSortieren} from '../../scripts/listen'
import {codeAnzeige} from '../../scripts/code'
import {leererHinweisCode, leererHinweisText, naechste} from '../../interfaces/Alarm'
import type {Alarm, Hinweis} from '../../interfaces/Alarm'
import type {SnaTreffer} from '../../interfaces/Sna'

const alarm = defineModel<Alarm>({required: true})
const abfrage = ref(false)

/**
 * The path through the interrogation is the Hinweis: its answers print as the numbered
 * sentences after the code. Kurzinfo and Stichwort come along, but only where they are empty —
 * an answer already given by hand is never overwritten.
 */
function uebernehmen(treffer: SnaTreffer, meldung: string) {
  // Where the crew has to go is not part of the path to a determinant, so it stands as its own
  // Hinweis — and before the code, because it is read first.
  for (const schritt of treffer.pfad.filter(s => s.eigen && s.aussage.trim())) {
    alarm.value.hinweise.push({
      ...leererHinweisText(naechste(alarm.value.hinweise)),
      text: schritt.aussage,
    })
  }
  alarm.value.hinweise.push({
    ...leererHinweisCode(naechste(alarm.value.hinweise)),
    code: treffer.code,
    meldung,
    antworten: treffer.pfad.filter(s => !s.eigen).map(s => s.aussage).filter(Boolean),
  })
  if (!alarm.value.kurzinfo) alarm.value.kurzinfo = treffer.anlass
  if (!alarm.value.stichwort) alarm.value.stichwort = treffer.stichwort
  abfrage.value = false
}

function textHinzufuegen() {
  alarm.value.hinweise.push(leererHinweisText(naechste(alarm.value.hinweise)))
}

function codeHinzufuegen() {
  alarm.value.hinweise.push(leererHinweisCode(naechste(alarm.value.hinweise)))
}

function entfernen(index: number) {
  alarm.value.hinweise.splice(index, 1)
}

function hinweisVerschieben(index: number, richtung: -1 | 1) {
  neuSortieren(alarm.value.hinweise, index, richtung)
}

function antwortHinzufuegen(hinweis: Hinweis) {
  if (hinweis.typ === 'code') hinweis.antworten.push('')
}

function antwortEntfernen(hinweis: Hinweis, index: number) {
  if (hinweis.typ === 'code') hinweis.antworten.splice(index, 1)
}

</script>

<template>
  <section class="abschnitt">
    <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
      <h2 class="abschnitt-titel">{{ t('abschnitt.hinweise') }}</h2>
      <div class="flex gap-2">
        <button type="button" class="knopf knopf-klein knopf-primaer" @click="abfrage = true">
          <font-awesome-icon icon="fa-solid fa-list-check"/>
          {{ t('sna.oeffnen') }}
        </button>
        <button type="button" class="knopf knopf-klein" @click="textHinzufuegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('hinweise.neuerText') }}
        </button>
        <button type="button" class="knopf knopf-klein" @click="codeHinzufuegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('hinweise.neuerCode') }}
        </button>
      </div>
    </div>

    <p v-if="!alarm.hinweise.length" class="text-muted text-sm">{{ t('hinweise.leer') }}</p>

    <ul class="grid gap-3">
      <li v-for="(hinweis, index) in alarm.hinweise" :key="index"
          class="border border-rule rounded p-3 bg-page">
        <div class="flex items-start gap-2">
          <div class="grow grid gap-2">
            <input v-if="hinweis.typ === 'text'" v-model="hinweis.text" type="text" class="field"
                   :placeholder="t('hinweise.platzhalterText')"/>

            <template v-else>
              <div class="grid md:grid-cols-[160px_1fr] gap-2">
                <div>
                  <label class="feld-label">{{ t('hinweise.code') }}</label>
                  <input v-model="hinweis.code" type="text" class="field"
                         :placeholder="t('hinweise.platzhalterCode')"/>
                </div>
                <div>
                  <label class="feld-label">{{ t('hinweise.meldung') }}</label>
                  <input v-model="hinweis.meldung" type="text" class="field"/>
                </div>
              </div>
              <div>
                <label class="feld-label">{{ t('hinweise.antworten') }}</label>
                <ol class="grid gap-2">
                  <li v-for="(_, nummer) in hinweis.antworten" :key="nummer" class="flex gap-2 items-center">
                    <span class="tabular text-muted text-[13px] w-6 text-right shrink-0">{{ nummer + 1 }}.</span>
                    <input v-model="hinweis.antworten[nummer]" type="text" class="field"/>
                    <button type="button" class="knopf knopf-klein knopf-gefahr shrink-0"
                            :title="t('hinweise.entfernen')" @click="antwortEntfernen(hinweis, nummer)">
                      <font-awesome-icon icon="fa-solid fa-xmark"/>
                    </button>
                  </li>
                </ol>
                <button type="button" class="knopf knopf-klein mt-2" @click="antwortHinzufuegen(hinweis)">
                  <font-awesome-icon icon="fa-solid fa-plus"/>
                  {{ t('hinweise.antwortHinzufuegen') }}
                </button>
              </div>
              <p v-if="hinweis.code" class="tabular text-[13px] text-muted">
                Code: {{ codeAnzeige(hinweis.code) }}
              </p>
            </template>
          </div>

          <div class="flex flex-col gap-1 shrink-0">
            <button type="button" class="knopf knopf-klein" :title="t('liste.hoch')"
                    :disabled="index === 0" @click="hinweisVerschieben(index, -1)">
              <font-awesome-icon icon="fa-solid fa-angle-up"/>
            </button>
            <button type="button" class="knopf knopf-klein" :title="t('liste.runter')"
                    :disabled="index === alarm.hinweise.length - 1" @click="hinweisVerschieben(index, 1)">
              <font-awesome-icon icon="fa-solid fa-angle-down"/>
            </button>
            <button type="button" class="knopf knopf-klein knopf-gefahr" :title="t('hinweise.entfernen')"
                    @click="entfernen(index)">
              <font-awesome-icon icon="fa-solid fa-trash"/>
            </button>
          </div>
        </div>
      </li>
    </ul>

    <SnaDialog v-if="abfrage" @schliessen="abfrage = false" @uebernehmen="uebernehmen"/>
  </section>
</template>
