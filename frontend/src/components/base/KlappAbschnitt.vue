<script setup lang="ts">
import {ref, watch} from 'vue'

/**
 * Ein Abschnitt, der sich zuklappen lässt.
 *
 * Der Katalog führt inzwischen elf Listen; alle gleichzeitig offen ist eine Seite, durch die man
 * scrollt, statt sie zu lesen. Was offen war, merkt sich der Browser — es gehört zu ihm und
 * nicht zur Arbeitsmappe, so wie das Farbthema.
 */
const {name, titel, anzahl} = defineProps<{
  /** Schlüssel, unter dem der Zustand gemerkt wird. */
  name: string
  titel: string
  /** Was drinsteht, ohne aufzuklappen. */
  anzahl?: number
}>()

const SPEICHER = 'alarmplaner_kataloge'

function gemerkt(): boolean {
  try {
    return Boolean(JSON.parse(localStorage.getItem(SPEICHER) ?? '{}')[name])
  } catch {
    return false
  }
}

const offen = ref(gemerkt())

watch(offen, wert => {
  try {
    const stand = JSON.parse(localStorage.getItem(SPEICHER) ?? '{}')
    localStorage.setItem(SPEICHER, JSON.stringify({...stand, [name]: wert}))
  } catch { /* ein Browser ohne Speicher klappt eben jedes Mal neu auf */ }
})
</script>

<template>
  <section class="abschnitt">
    <div class="flex items-center gap-3 flex-wrap">
      <button type="button" class="flex items-center gap-3 grow text-left" @click="offen = !offen">
        <font-awesome-icon :icon="offen ? 'fa-solid fa-angle-down' : 'fa-solid fa-angle-right'"
                           class="text-muted"/>
        <h2 class="abschnitt-titel mb-0">{{ titel }}</h2>
        <span v-if="anzahl !== undefined" class="text-muted tabular text-sm">{{ anzahl }}</span>
      </button>
      <slot v-if="offen" name="werkzeug"/>
    </div>

    <div v-if="offen" class="mt-3">
      <slot/>
    </div>
  </section>
</template>
