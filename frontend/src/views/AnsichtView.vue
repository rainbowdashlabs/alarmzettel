<script setup lang="ts">
import {computed, ref} from 'vue'
import AlarmKarte from '../components/alarm/AlarmKarte.vue'
import LagenAnsicht from '../components/planung/LagenAnsicht.vue'
import PersonenPlan from '../components/planung/PersonenPlan.vue'
import OrtsSicht from '../components/planung/OrtsSicht.vue'
import {t} from '../i18n'
import {arbeitsmappe} from '../store/arbeitsmappe'
import {renderAlle, fehlertext} from '../api/render'
import {jetztAbgleichen} from '../store/sync'

/**
 * Die Arbeitsmappe zum Lesen: dieselben Angaben wie in den Editoren, nur als Seite. Das ist die
 * Ansicht hinter einem Lesen-Link — wer zusieht, will den Stand sehen und nicht in Felder blicken,
 * in denen er ohnehin nichts ändern kann.
 */
const ANSICHTEN = ['alarme', 'einsaetze', 'personen', 'orte'] as const
const ansicht = ref<typeof ANSICHTEN[number]>('alarme')
const fehler = ref<string | null>(null)

const geplant = computed(() => arbeitsmappe.planung.aktiv)
const reiter = computed(() =>
    geplant.value ? ANSICHTEN : ANSICHTEN.filter(name => name === 'alarme'))

async function pdf() {
  fehler.value = null
  try {
    await jetztAbgleichen()
    const url = URL.createObjectURL(await renderAlle())
    const link = document.createElement('a')
    link.href = url
    link.download = 'alarmzettel.pdf'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}
</script>

<template>
  <div class="grid gap-5">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="headline text-2xl">{{ t('ansicht.titel') }}</h1>
        <p class="text-muted text-sm mt-1">{{ t('ansicht.beschreibung') }}</p>
      </div>
      <button type="button" class="knopf" :disabled="!arbeitsmappe.alarme.length" @click="pdf">
        <font-awesome-icon icon="fa-solid fa-file-pdf"/>
        {{ t('datei.pdfAlle') }}
      </button>
    </div>

    <p v-if="fehler" class="text-sm text-signal-ink">{{ fehler }}</p>

    <div v-if="reiter.length > 1" class="flex flex-wrap gap-2">
      <button v-for="name in reiter" :key="name" type="button" class="knopf knopf-klein"
              :class="ansicht === name ? 'knopf-primaer' : ''" @click="ansicht = name">
        {{ t(`ansicht.reiter.${name}`) }}
      </button>
    </div>

    <template v-if="ansicht === 'alarme'">
      <p v-if="!arbeitsmappe.alarme.length" class="text-muted text-sm">{{ t('liste.leer') }}</p>
      <AlarmKarte v-for="alarm in arbeitsmappe.alarme" :key="alarm.id" :alarm="alarm"/>
    </template>

    <LagenAnsicht v-else-if="ansicht === 'einsaetze'"/>
    <PersonenPlan v-else-if="ansicht === 'personen'"/>
    <OrtsSicht v-else-if="ansicht === 'orte'"/>
  </div>
</template>
