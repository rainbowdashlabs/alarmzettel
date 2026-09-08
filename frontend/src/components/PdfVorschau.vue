<script setup lang="ts">
import {computed, onBeforeUnmount, ref, watch} from 'vue'
import {t} from '../i18n'
import {fehlertext} from '../api/render'

const props = defineProps<{ rendern: () => Promise<Blob>, ausloeser: unknown }>()

const url = ref<string | null>(null)
/** The viewer's own toolbar and thumbnail rail only take room from the sheet. */
const angezeigt = computed(() => url.value ? `${url.value}#toolbar=0&navpanes=0&view=FitH` : null)
const laedt = ref(false)
const fehler = ref<string | null>(null)
let timer: number | undefined
let lauf = 0

/**
 * The preview is the same Typst render as the download, so it cannot disagree with what prints.
 * Edits are debounced; a slow render that has been superseded is discarded rather than shown.
 */
async function erzeugen() {
  const meine = ++lauf
  laedt.value = true
  fehler.value = null
  try {
    const blob = await props.rendern()
    if (meine !== lauf) return
    if (url.value) URL.revokeObjectURL(url.value)
    url.value = URL.createObjectURL(blob)
  } catch (error) {
    if (meine !== lauf) return
    fehler.value = await fehlertext(error)
  } finally {
    if (meine === lauf) laedt.value = false
  }
}

watch(() => props.ausloeser, () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(erzeugen, 400)
}, {deep: true, immediate: true})

onBeforeUnmount(() => {
  window.clearTimeout(timer)
  if (url.value) URL.revokeObjectURL(url.value)
})
</script>

<template>
  <div class="abschnitt h-full flex flex-col">
    <div class="flex items-center justify-between mb-3 gap-2">
      <h2 class="abschnitt-titel mb-0">{{ t('abschnitt.vorschau') }}</h2>
      <span v-if="laedt" class="label">{{ t('vorschau.laedt') }}</span>
    </div>

    <div v-if="fehler" class="grow flex flex-col items-center justify-center gap-3 text-center p-4">
      <p class="text-signal-ink text-sm">{{ fehler }}</p>
      <button type="button" class="knopf" @click="erzeugen">{{ t('vorschau.erneut') }}</button>
    </div>

    <iframe v-else-if="angezeigt" :src="angezeigt" class="grow w-full border border-rule rounded bg-white"
            title="PDF"/>

    <p v-else class="grow flex items-center justify-center text-muted text-sm">
      {{ t('vorschau.leer') }}
    </p>
  </div>
</template>
