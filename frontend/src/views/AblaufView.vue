<script setup lang="ts">
import {watch} from 'vue'
import {RouterLink} from 'vue-router'
import LaufKette from '../components/planung/LaufKette.vue'
import {t} from '../i18n'
import {arbeitsmappe} from '../store/arbeitsmappe'
import {entfernen, laufAnlegen, laufVon, personName, punkteLaden} from '../store/planung'

watch(() => arbeitsmappe.planung.orte.map(ort => Object.values(ort.adresse).join()).join('|'),
    () => punkteLaden(), {immediate: true})

/** Ein Fahrzeug oder eine Person bekommt eine Kette, sobald es eingeplant wird. */
function einplanen(fuer: {fahrzeugId?: string, personId?: string}) {
  if (!laufVon(fuer)) laufAnlegen(fuer)
}

function beschriftung(lauf: {fahrzeugId: string, personId: string}): string {
  if (lauf.fahrzeugId) {
    return arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === lauf.fahrzeugId)?.funkrufname
        || t('ablauf.ohneName')
  }
  return personName(lauf.personId) || t('ablauf.ohneName')
}

function offen(fuer: {fahrzeugId?: string, personId?: string}): boolean {
  return !laufVon(fuer)
}
</script>

<template>
  <div class="grid gap-5">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="headline text-2xl">{{ t('ablauf.titel') }}</h1>
        <p class="text-muted text-sm mt-1">{{ t('ablauf.beschreibung') }}</p>
      </div>
      <RouterLink to="/planung" class="knopf knopf-klein">{{ t('ablauf.stammdaten') }}</RouterLink>
    </div>

    <section v-if="!arbeitsmappe.planung.orte.length" class="abschnitt">
      <p class="text-muted text-sm">{{ t('ablauf.ersteOrte') }}</p>
    </section>

    <section class="abschnitt">
      <h2 class="abschnitt-titel">{{ t('ablauf.einplanen') }}</h2>
      <div class="flex flex-wrap gap-2">
        <button v-for="fahrzeug in arbeitsmappe.kataloge.fahrzeuge.filter(v => offen({fahrzeugId: v.id}))"
                :key="fahrzeug.id" type="button" class="knopf knopf-klein"
                @click="einplanen({fahrzeugId: fahrzeug.id})">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ fahrzeug.funkrufname || t('ablauf.ohneName') }}
        </button>
        <button v-for="person in arbeitsmappe.planung.personen.filter(p => offen({personId: p.id}))"
                :key="person.id" type="button" class="knopf knopf-klein"
                @click="einplanen({personId: person.id})">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ person.name || t('ablauf.ohneName') }}
        </button>
      </div>
      <p class="text-muted text-[13px] mt-2">{{ t('ablauf.einplanenHinweis') }}</p>
    </section>

    <p v-if="!arbeitsmappe.planung.laeufe.length" class="text-muted text-sm">
      {{ t('ablauf.keineKetten') }}
    </p>

    <section v-for="lauf in arbeitsmappe.planung.laeufe" :key="lauf.id" class="abschnitt">
      <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <h2 class="abschnitt-titel mb-0">
          <font-awesome-icon :icon="lauf.fahrzeugId ? 'fa-solid fa-table' : 'fa-solid fa-users'"
                             class="mr-2 text-muted"/>
          {{ beschriftung(lauf) }}
        </h2>
        <button type="button" class="knopf knopf-klein knopf-gefahr"
                @click="entfernen(arbeitsmappe.planung.laeufe, lauf)">
          <font-awesome-icon icon="fa-solid fa-trash"/>
          {{ t('ablauf.ketteEntfernen') }}
        </button>
      </div>
      <LaufKette :lauf="lauf"/>
    </section>
  </div>
</template>
