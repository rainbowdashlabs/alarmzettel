<script setup lang="ts">
import {onMounted, ref} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {t} from '../i18n'
import {sitzungLesen} from '../api/sitzung'
import {fehlertext} from '../api/render'
import {arbeitsmappe, ersetzen, uebernehmen} from '../store/arbeitsmappe'
import {sitzungWechseln, nameSetzen} from '../store/sitzung'
import Rueckfrage from '../components/base/Rueckfrage.vue'
import type {GeleseneSitzung} from '../api/sitzung'

const route = useRoute()
const router = useRouter()
const freigabe = ref<GeleseneSitzung | null>(null)
const fehler = ref<string | null>(null)
const name = ref(localStorage.getItem('alarmzettel_name') ?? '')
const rueckfrage = ref<'mitarbeiten' | 'kopie' | null>(null)

onMounted(async () => {
  try {
    freigabe.value = await sitzungLesen(String(route.params.token))
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
})

/** The shared copy replaces what is in this browser, so the existing set is not lost silently. */
function kopieAnfordern() {
  if (!freigabe.value) return
  if (arbeitsmappe.alarme.length) rueckfrage.value = 'kopie'
  else kopieUebernehmen()
}

function kopieUebernehmen() {
  if (!freigabe.value) return
  rueckfrage.value = null
  ersetzen(uebernehmen(freigabe.value.arbeitsmappe))
  router.push('/')
}

/**
 * Joining replaces what is in this browser with the workspace. A shared room is not merged with
 * whatever happened to be open here, or one person's leftovers would land on everyone else.
 */
function mitarbeitenAnfordern() {
  if (!freigabe.value || !(name.value.trim() || freigabe.value.nurLesen)) return
  if (arbeitsmappe.alarme.length) rueckfrage.value = 'mitarbeiten'
  else void mitarbeiten()
}

/** Mit einem Lesetoken heißt dasselbe „ansehen“: der Browser folgt der Sitzung, ohne zu schreiben. */
async function mitarbeiten() {
  if (!freigabe.value) return
  rueckfrage.value = null
  if (name.value.trim()) localStorage.setItem('alarmzettel_name', name.value.trim())
  try {
    nameSetzen(name.value)
    await sitzungWechseln(String(route.params.token))
    router.push('/')
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}

function datum(wert: string): string {
  return new Date(wert).toLocaleDateString('de-DE', {day: '2-digit', month: '2-digit', year: 'numeric'})
}
</script>

<template>
  <div class="grid gap-5 max-w-2xl">
    <h1 class="headline text-2xl">{{ t('freigabe.titel') }}</h1>

    <p v-if="fehler" class="abschnitt text-signal-ink">{{ fehler }}</p>
    <p v-else-if="!freigabe" class="text-muted text-sm">{{ t('freigabe.laedt') }}</p>

    <div v-else class="abschnitt grid gap-3">
      <p>{{ t('freigabe.enthaelt', freigabe.arbeitsmappe.alarme.length) }}</p>
      <ul class="grid gap-1">
        <li v-for="alarm in freigabe.arbeitsmappe.alarme" :key="alarm.id" class="text-sm">
          <span class="tabular text-muted mr-2">{{ alarm.einsatzNr }}</span>
          <span class="font-condensed font-bold uppercase tracking-wide">
            {{ alarm.stichwort || t('liste.ohneStichwort') }}
          </span>
          <span class="text-muted ml-2">{{ alarm.kurzinfo }}</span>
        </li>
      </ul>
      <p class="text-muted text-[13px]">{{ t('freigabe.laeuftAb', {datum: datum(freigabe.laeuftAb)}) }}</p>
      <div v-if="freigabe.nurLesen" class="grid gap-2 border-t border-rule pt-3">
        <button type="button" class="knopf knopf-primaer justify-self-start"
                @click="mitarbeitenAnfordern">
          <font-awesome-icon icon="fa-solid fa-users"/>
          {{ t('freigabe.ansehen') }}
        </button>
        <p class="text-muted text-[13px]">{{ t('freigabe.ansehenHinweis') }}</p>
      </div>

      <div v-else class="grid gap-2 border-t border-rule pt-3">
        <label class="feld-label" for="wer">{{ t('freigabe.name') }}</label>
        <div class="flex gap-2 flex-wrap">
          <input id="wer" v-model="name" type="text" class="field grow min-w-40"
                 :placeholder="t('freigabe.namePlatzhalter')"/>
          <button type="button" class="knopf knopf-primaer shrink-0"
                  :disabled="!name.trim()" @click="mitarbeitenAnfordern">
            <font-awesome-icon icon="fa-solid fa-users"/>
            {{ t('freigabe.mitarbeiten') }}
          </button>
        </div>
        <p class="text-muted text-[13px]">{{ t('freigabe.mitarbeitenHinweis') }}</p>
      </div>

      <div class="border-t border-rule pt-3">
        <button type="button" class="knopf" @click="kopieAnfordern">
          <font-awesome-icon icon="fa-solid fa-download"/>
          {{ t('freigabe.uebernehmen') }}
        </button>
        <p class="text-muted text-[13px] mt-2">{{ t('freigabe.kopieHinweis') }}</p>
      </div>
    </div>

    <Rueckfrage v-if="rueckfrage" :frage="t('datei.ersetzen')"
                @nein="rueckfrage = null"
                @ja="rueckfrage === 'mitarbeiten' ? mitarbeiten() : kopieUebernehmen()"/>
  </div>
</template>
