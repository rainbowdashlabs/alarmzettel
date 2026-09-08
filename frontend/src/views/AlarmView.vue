<script setup lang="ts">
import {computed, ref} from 'vue'
import {useRoute} from 'vue-router'
import AlarmKopf from '../components/alarm/AlarmKopf.vue'
import AlarmAdressen from '../components/alarm/AlarmAdressen.vue'
import AlarmBeteiligte from '../components/alarm/AlarmBeteiligte.vue'
import AlarmHinweise from '../components/alarm/AlarmHinweise.vue'
import AlarmEinsatzmittel from '../components/alarm/AlarmEinsatzmittel.vue'
import PdfVorschau from '../components/PdfVorschau.vue'
import {t} from '../i18n'
import {alarmFinden} from '../store/arbeitsmappe'
import {fehlertext, renderEinen} from '../api/render'
import {jetztAbgleichen} from '../store/sync'

const route = useRoute()
const fehler = ref<string | null>(null)
const alarm = computed(() => alarmFinden(String(route.params.id)))

function rendern(): Promise<Blob> {
  return renderEinen(String(route.params.id))
}

async function pdf() {
  fehler.value = null
  try {
    // Exchanged first, so the sheet is printed from what everyone has rather than from what this
    // browser happened to see a few seconds ago. Outside a shared workspace this does nothing.
    await jetztAbgleichen()
    const blob = await rendern()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `alarmzettel-${alarm.value?.einsatzNr || 'alarm'}.pdf`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}
</script>

<template>
  <div v-if="!alarm" class="abschnitt text-center py-10">
    <p>{{ t('nichtGefunden.titel') }}</p>
    <RouterLink to="/" class="knopf mt-3 inline-flex">{{ t('nichtGefunden.zurueck') }}</RouterLink>
  </div>

  <div v-else class="grid gap-5">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div class="flex items-center gap-3">
        <RouterLink to="/" class="knopf knopf-klein">
          <font-awesome-icon icon="fa-solid fa-arrow-left"/>
          {{ t('aktion.zurueck') }}
        </RouterLink>
        <h1 class="headline text-2xl">
          {{ alarm.stichwort || t('liste.ohneStichwort') }}
        </h1>
      </div>
      <button type="button" class="knopf" @click="pdf">
        <font-awesome-icon icon="fa-solid fa-file-pdf"/>
        {{ t('datei.pdfEiner') }}
      </button>
    </div>

    <p v-if="fehler" class="text-sm text-signal-ink">{{ fehler }}</p>

    <div class="grid xl:grid-cols-[minmax(0,1fr)_minmax(360px,44%)] gap-5 items-start">
      <div class="grid gap-4 min-w-0">
        <AlarmKopf v-model="alarm"/>
        <AlarmAdressen v-model="alarm"/>
        <AlarmBeteiligte v-model="alarm"/>
        <AlarmHinweise v-model="alarm"/>
        <AlarmEinsatzmittel v-model="alarm"/>
      </div>

      <div class="xl:sticky xl:top-5 h-[75vh] min-h-100">
        <PdfVorschau :rendern="rendern" :ausloeser="alarm"/>
      </div>
    </div>
  </div>
</template>
