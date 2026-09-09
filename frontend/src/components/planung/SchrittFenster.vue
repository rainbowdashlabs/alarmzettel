<script setup lang="ts">
import SchrittFelder from './SchrittFelder.vue'
import {t} from '../../i18n'
import {entfernen, mehrereTage} from '../../store/planung'
import {tagVon, uhrzeit} from '../../scripts/zeit'
import type {Lauf, Schritt} from '../../interfaces/Planung'

/** Ein Schritt zum Ändern, über dem Tagesplan. Dieselben Felder wie in der Kette. */
const {lauf, schritt, name} = defineProps<{ lauf: Lauf, schritt: Schritt, name: string }>()
const meldet = defineEmits<{ schliessen: [] }>()

function wegwerfen() {
  entfernen(lauf.schritte, schritt)
  meldet('schliessen')
}
</script>

<template>
  <div class="fixed inset-0 z-50 bg-black/55 flex items-start justify-center p-4 overflow-auto"
       @click.self="meldet('schliessen')">
    <div class="abschnitt w-full max-w-3xl my-6 grid gap-3">
      <div class="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 class="abschnitt-titel">{{ name }}</h2>
          <p class="tabular text-sm text-muted mt-1">
            <span v-if="mehrereTage()">{{ tagVon(schritt.von) }} </span>
            {{ uhrzeit(schritt.von) }}–{{ uhrzeit(schritt.bis) }}
          </p>
        </div>
        <div class="flex gap-2 flex-wrap">
          <button type="button" class="knopf knopf-klein knopf-gefahr" @click="wegwerfen">
            <font-awesome-icon icon="fa-solid fa-trash"/>
            {{ t('ablauf.schrittEntfernen') }}
          </button>
          <button type="button" class="knopf knopf-klein" @click="meldet('schliessen')">
            <font-awesome-icon icon="fa-solid fa-xmark"/>
            {{ t('aktion.schliessen') }}
          </button>
        </div>
      </div>

      <SchrittFelder :lauf="lauf" :schritt="schritt"/>
    </div>
  </div>
</template>
