<script setup lang="ts">
import {ref} from 'vue'
import AdresseFeld from '../components/base/AdresseFeld.vue'
import TextFeld from '../components/base/TextFeld.vue'
import {t} from '../i18n'
import {arbeitsmappe} from '../store/arbeitsmappe'
import {truppText} from '../scripts/staerke'
import type {Kataloge} from '../interfaces/Alarm'

type Wortliste = Extract<keyof Kataloge, 'stichwoerter' | 'status' | 'trupp'>

const listen: { schluessel: Wortliste, titel: string }[] = [
  {schluessel: 'stichwoerter', titel: t('kataloge.stichwoerter')},
  {schluessel: 'status', titel: t('kataloge.status')},
  {schluessel: 'trupp', titel: t('kataloge.trupp')},
]

const entwurf = ref<Record<string, string>>({})

function hinzufuegen(schluessel: Wortliste) {
  const wert = (entwurf.value[schluessel] ?? '').trim()
  if (!wert || arbeitsmappe.kataloge[schluessel].includes(wert)) return
  arbeitsmappe.kataloge[schluessel].push(wert)
  entwurf.value[schluessel] = ''
}

function entfernen(schluessel: Wortliste, index: number) {
  arbeitsmappe.kataloge[schluessel].splice(index, 1)
}

function fahrzeugHinzufuegen() {
  arbeitsmappe.kataloge.fahrzeuge.push({funkrufname: '', staerke: '', ezp: '', status: ''})
}

function fahrzeugEntfernen(index: number) {
  arbeitsmappe.kataloge.fahrzeuge.splice(index, 1)
}

/** Shows what the strength will print as, so a wrong number is visible before it is used. */
function truppVorschau(staerke: string): string {
  const zahl = Number(staerke)
  return Number.isFinite(zahl) && zahl > 0 ? truppText(zahl) : ''
}
</script>

<template>
  <div class="grid gap-5">
    <div>
      <h1 class="headline text-2xl">{{ t('kataloge.titel') }}</h1>
      <p class="text-muted text-sm mt-1">{{ t('kataloge.beschreibung') }}</p>
    </div>

    <section class="abschnitt">
      <h2 class="abschnitt-titel">{{ t('kataloge.dienststelle') }}</h2>
      <div class="grid md:grid-cols-3 gap-3">
        <TextFeld v-model="arbeitsmappe.kataloge.arbeitsgruppe" :label="t('feld.arbeitsgruppe')"/>
      </div>
      <p class="text-muted text-[13px] mt-3 mb-4">{{ t('kataloge.arbeitsgruppeHinweis') }}</p>

      <AdresseFeld v-model="arbeitsmappe.kataloge.wache" :titel="t('kataloge.wache')"/>
      <p class="text-muted text-[13px] mt-3">{{ t('kataloge.wacheHinweis') }}</p>
    </section>

    <section class="abschnitt">
      <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <h2 class="abschnitt-titel mb-0">{{ t('kataloge.fahrzeuge') }}</h2>
        <button type="button" class="knopf knopf-klein" @click="fahrzeugHinzufuegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('kataloge.hinzufuegen') }}
        </button>
      </div>
      <p class="text-muted text-[13px] mb-3">{{ t('kataloge.fahrzeugeHinweis') }}</p>

      <p v-if="!arbeitsmappe.kataloge.fahrzeuge.length" class="text-muted text-sm">
        {{ t('kataloge.leer') }}
      </p>

      <div class="grid gap-2">
        <div v-for="(fahrzeug, index) in arbeitsmappe.kataloge.fahrzeuge" :key="index"
             class="grid md:grid-cols-[1fr_auto] gap-2 items-end">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
            <TextFeld v-model="fahrzeug.funkrufname" :label="t('feld.funkrufname')"/>
            <TextFeld v-model="fahrzeug.staerke" :label="t('feld.staerke')"/>
            <TextFeld v-model="fahrzeug.ezp" :label="t('feld.ezp')"/>
            <TextFeld v-model="fahrzeug.status" :label="t('feld.status')"/>
          </div>
          <button type="button" class="knopf knopf-klein knopf-gefahr"
                  :title="t('kataloge.eintragEntfernen')" @click="fahrzeugEntfernen(index)">
            <font-awesome-icon icon="fa-solid fa-xmark"/>
          </button>
          <p v-if="truppVorschau(fahrzeug.staerke)" class="tabular text-[13px] text-muted md:col-span-2">
            {{ truppVorschau(fahrzeug.staerke) }}
          </p>
        </div>
      </div>
    </section>

    <div class="grid md:grid-cols-3 gap-4">
      <section v-for="liste in listen" :key="liste.schluessel" class="abschnitt">
        <h2 class="abschnitt-titel">{{ liste.titel }}</h2>

        <form class="flex gap-2 mb-3" @submit.prevent="hinzufuegen(liste.schluessel)">
          <input v-model="entwurf[liste.schluessel]" type="text" class="field"/>
          <button type="submit" class="knopf shrink-0">
            <font-awesome-icon icon="fa-solid fa-plus"/>
          </button>
        </form>

        <p v-if="!arbeitsmappe.kataloge[liste.schluessel].length" class="text-muted text-sm">
          {{ t('kataloge.leer') }}
        </p>

        <ul class="flex flex-wrap gap-2">
          <li v-for="(wert, index) in arbeitsmappe.kataloge[liste.schluessel]" :key="wert"
              class="flex items-center gap-2 border border-rule rounded px-2 py-1 bg-page">
            <span class="text-sm">{{ wert }}</span>
            <button type="button" class="text-muted hover:text-signal"
                    :title="t('kataloge.eintragEntfernen')"
                    @click="entfernen(liste.schluessel, index)">
              <font-awesome-icon icon="fa-solid fa-xmark"/>
            </button>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
