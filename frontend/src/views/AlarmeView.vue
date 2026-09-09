<script setup lang="ts">
import {ref} from 'vue'
import {useRouter} from 'vue-router'
import {t} from '../i18n'
import {
    alarmAnlegen, alarmKopieren, alarmLoeschen, alarmVerschieben, arbeitsmappe, ersetzen, uebernehmen,
} from '../store/arbeitsmappe'
import {renderAlle, fehlertext} from '../api/render'
import {tabelleImportieren} from '../api/tabelle'
import {sitzung} from '../store/sitzung'
import Rueckfrage from '../components/base/Rueckfrage.vue'
import {jetztAbgleichen} from '../store/sync'

const router = useRouter()
const datei = ref<HTMLInputElement>()
const tabelle = ref<HTMLInputElement>()
const meldung = ref<string | null>(null)
const fehler = ref<string | null>(null)
const freigabeLink = ref<string | null>(null)
const anstehend = ref<(() => void) | null>(null)

/** Asks before replacing a working set that has something in it, without blocking the page. */
function ersetzenLassen(tun: () => void) {
  if (arbeitsmappe.alarme.length) anstehend.value = tun
  else tun()
}

function anlegen() {
  router.push(`/alarm/${alarmAnlegen().id}`)
}

async function herunterladen() {
  // Exchanged first, so the saved file holds what everyone has. Outside a shared workspace this
  // does nothing.
  await jetztAbgleichen()
  speichern(new Blob([JSON.stringify(arbeitsmappe, null, 2)], {type: 'application/json'}),
      'alarmplaner.json')
}

async function pdf() {
  fehler.value = null
  try {
    // Exchanged first, so the sheets are printed from what everyone has rather than from what
    // this browser happened to see a few seconds ago. Outside a shared workspace this does
    // nothing.
    await jetztAbgleichen()
    speichern(await renderAlle(), 'alarmzettel.pdf')
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}

/**
 * Teilen heißt: den Link zu dieser Sitzung weitergeben. Es gibt nichts anzulegen — die
 * Arbeitsmappe liegt schon auf dem Server, und der Link darauf ist der Schlüssel dazu.
 */
async function teilenLassen() {
  fehler.value = null
  meldung.value = null
  try {
    // Vor dem Weitergeben abgleichen, damit der andere den aktuellen Stand sieht.
    await jetztAbgleichen()
    freigabeLink.value = sitzung.token
        ? `${window.location.origin}/sitzung/${sitzung.token}`
        : null
    meldung.value = freigabeLink.value ? t('freigabe.erzeugt', {tage: 30}) : null
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}

async function linkKopieren() {
  if (!freigabeLink.value) return
  try {
    await navigator.clipboard.writeText(freigabeLink.value)
    meldung.value = t('freigabe.kopiert')
  } catch { /* a browser that refuses the clipboard still shows the link to select by hand */ }
}

function speichern(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}

/** The old spreadsheet: one row per Alarm, one vehicle, Hinweise squashed into one cell. */
async function tabelleLaden(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  fehler.value = null
  meldung.value = null
  try {
    const geladen = await tabelleImportieren(file)
    ersetzenLassen(() => {
      ersetzen(uebernehmen(geladen))
      meldung.value = t('datei.importiert', arbeitsmappe.alarme.length)
    })
  } catch (error) {
    fehler.value = await fehlertext(error)
  } finally {
    if (tabelle.value) tabelle.value.value = ''
  }
}

async function laden(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  fehler.value = null
  meldung.value = null
  try {
    const roh = JSON.parse(await file.text())
    ersetzenLassen(() => {
      ersetzen(uebernehmen(roh))
      meldung.value = t('datei.geladen')
    })
  } catch {
    fehler.value = t('datei.fehlerhaft')
  } finally {
    if (datei.value) datei.value.value = ''
  }
}
</script>

<template>
  <div class="grid gap-5">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="headline text-2xl">{{ t('nav.alarme') }}</h1>
        <p class="label mt-1">{{ t('liste.anzahl', arbeitsmappe.alarme.length) }}</p>
      </div>
      <div class="flex gap-2 flex-wrap">
        <button type="button" class="knopf" @click="tabelle?.click()">
          <font-awesome-icon icon="fa-solid fa-table"/>
          {{ t('datei.tabelle') }}
        </button>
        <button type="button" class="knopf" @click="datei?.click()">
          <font-awesome-icon icon="fa-solid fa-upload"/>
          {{ t('datei.hochladen') }}
        </button>
        <button type="button" class="knopf" :disabled="!arbeitsmappe.alarme.length" @click="herunterladen">
          <font-awesome-icon icon="fa-solid fa-download"/>
          {{ t('datei.herunterladen') }}
        </button>
        <button type="button" class="knopf" :disabled="!arbeitsmappe.alarme.length" @click="teilenLassen">
          <font-awesome-icon icon="fa-solid fa-share-nodes"/>
          {{ t('freigabe.teilen') }}
        </button>
        <button type="button" class="knopf" :disabled="!arbeitsmappe.alarme.length" @click="pdf">
          <font-awesome-icon icon="fa-solid fa-file-pdf"/>
          {{ t('datei.pdfAlle') }}
        </button>
        <button type="button" class="knopf knopf-primaer" @click="anlegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('liste.neu') }}
        </button>
      </div>
    </div>

    <input ref="datei" type="file" accept="application/json" class="hidden" @change="laden"/>
    <input ref="tabelle" type="file" class="hidden" @change="tabelleLaden"
           accept=".ods,.xlsx,application/vnd.oasis.opendocument.spreadsheet,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"/>

    <div v-if="freigabeLink" class="abschnitt grid gap-2">
      <div class="flex gap-2 items-center flex-wrap">
        <input :value="freigabeLink" readonly class="field grow min-w-60 tabular text-[13px]"/>
        <button type="button" class="knopf shrink-0" @click="linkKopieren">
          <font-awesome-icon icon="fa-solid fa-copy"/>
        </button>
      </div>
      <p class="text-signal-ink text-[13px]">{{ t('freigabe.warnung') }}</p>
    </div>

    <p v-if="meldung" class="text-sm text-muted">{{ meldung }}</p>
    <p v-if="fehler" class="text-sm text-signal-ink">{{ fehler }}</p>

    <div v-if="!arbeitsmappe.alarme.length" class="abschnitt text-center py-10">
      <p class="text-ink">{{ t('liste.leer') }}</p>
      <p class="text-muted text-sm mt-1">{{ t('liste.leerHinweis') }}</p>
    </div>

    <ul v-else class="grid gap-2">
      <li v-for="(alarm, index) in arbeitsmappe.alarme" :key="alarm.id"
          class="abschnitt flex items-center gap-3 flex-wrap">
        <span class="tabular text-muted w-8 shrink-0">{{ alarm.einsatzNr || index }}</span>
        <div class="grow min-w-40">
          <div class="font-condensed font-bold tracking-wide uppercase">
            {{ alarm.stichwort || t('liste.ohneStichwort') }}
          </div>
          <div class="text-sm text-muted">
            {{ alarm.kurzinfo }}
            <span v-if="alarm.einsatzadresse.strasse" class="tabular">
              · {{ alarm.einsatzadresse.strasse }} {{ alarm.einsatzadresse.hnr }}
            </span>
          </div>
        </div>
        <span class="label shrink-0">
          {{ alarm.einsatzDatum }} {{ alarm.einsatzZeit }}
        </span>
        <div class="flex gap-1 shrink-0">
          <button type="button" class="knopf knopf-klein" :title="t('liste.hoch')"
                  :disabled="index === 0" @click="alarmVerschieben(alarm.id, -1)">
            <font-awesome-icon icon="fa-solid fa-angle-up"/>
          </button>
          <button type="button" class="knopf knopf-klein" :title="t('liste.runter')"
                  :disabled="index === arbeitsmappe.alarme.length - 1"
                  @click="alarmVerschieben(alarm.id, 1)">
            <font-awesome-icon icon="fa-solid fa-angle-down"/>
          </button>
          <button type="button" class="knopf knopf-klein" :title="t('liste.kopieren')"
                  @click="alarmKopieren(alarm.id)">
            <font-awesome-icon icon="fa-solid fa-copy"/>
          </button>
          <button type="button" class="knopf knopf-klein knopf-gefahr" :title="t('liste.loeschen')"
                  @click="alarmLoeschen(alarm.id)">
            <font-awesome-icon icon="fa-solid fa-trash"/>
          </button>
          <RouterLink :to="`/alarm/${alarm.id}`" class="knopf knopf-klein">
            <font-awesome-icon icon="fa-solid fa-pen"/>
            {{ t('liste.oeffnen') }}
          </RouterLink>
        </div>
      </li>
    </ul>

    <Rueckfrage v-if="anstehend" :frage="t('datei.ersetzen')"
                @nein="anstehend = null"
                @ja="anstehend?.(); anstehend = null"/>
  </div>
</template>
